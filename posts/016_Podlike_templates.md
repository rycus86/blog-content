# Podlike templates

We've seen that we can run co-located and coupled services on Docker Swarm. This post shows you how to use templates to extend your services in a common way.

If you haven't done so already, check out the [introduction post](https://blog.viktoradam.net/2018/05/14/podlike/) and the [examples](https://blog.viktoradam.net/2018/05/24/podlike-example-use-cases/) to see what [Podlike](https://github.com/rycus86/podlike) can be used for. In short, you can get a set of containers to always run on the same node in Docker Swarm mode as a task of a service. These containers will share a network namespace, so it makes it very easy to run [sidecars](https://docs.microsoft.com/en-us/azure/architecture/patterns/sidecar) for example. You can also share PID namespaces and volumes, that enables using different patterns for coupled applications.

## The problem

While I was working on the [demo examples](https://github.com/rycus86/podlike/tree/master/examples), one thing became clear to me. If you have homogeneous applications, and you always want to *decorate* them with the same components, then there can be an awful lot of duplication in the stack YAML pretty quickly. In the [biggest stack](https://github.com/rycus86/podlike/blob/master/examples/modernized/stack.yml), each of the applications we want to run in a [service mesh](https://www.thoughtworks.com/radar/techniques/service-mesh) is coupled with the same: a [Traefik](https://traefik.io/) reverse proxy, a [Consul](https://www.consul.io/) agent for service discovery support, a [Jaeger](https://www.jaegertracing.io/) agent for distributed tracing, and a [Fluent Bit](https://fluentbit.io/) instance for centralized logging.

The configuration is almost identical for each service, with the exception of service names and log file paths. Do we really have to duplicate their definitions then? Surely, there's a better way.

## Templates to the rescue

We have identified that the component configurations really only differ in a few variables, but the rest of it could easily be templated. Why not do exactly that then?

In version `0.3.x` of the app, I've added support for transforming a set of [Compose files](https://docs.docker.com/compose/compose-file/) into a single YAML, that changes the services you want into *"pods"*, while still being compatible with the format `docker stack deploy` expects. Actually, with the help of [extension fields](https://docs.docker.com/compose/compose-file/#extension-fields), you can decide whether you want to deploy the stack as-is, or the templated version with the coupled components in it. This could be useful, if you don't necessarily need all those extra bits for local development, but would want to have them on the target servers or environment.

> Top-level extension fields are supported on Compose schema version 3.4 and above.

You can have a *top-level* extension field, called `x-podlike`, that can define 4 types of templates for each individual service:

1. `pod` that generates the result Swarm service definition
2. `transformer` to generate the configuration for the main component
3. `templates` to produce any additional components
4. `copy` for generating the configuration for the files to copy into the component containers

Each of these can define one of more [templates](TODO link to podlike template docs) to use, either inline, from local files, or fetched from an HTTP(s) URL. The templates need to produce YAML snippets using Go's [text/template package](https://golang.org/pkg/text/template/) to transform the original service definition and any additional arguments into the new controller/components configuration. Let me show an example of how this looks like.

```yaml
version: '3.5'

x-podlike:
  # template the `site` service
  site:
    pod:
	  
	  # template for the controller
	  inline:
	    pod:
		  # image will default to rycus86/podlike
		  command: -logs
		  configs:
		    - source: nginx-conf
			  target: /var/conf/nginx.conf
		  ports:
		    - 8080:80
		  # the `/var/run/docker.sock` volume is also added by default

    transformer:
	  # template for the main component
	  inline: |
	    app:
		  environment: # override environment variables
		    - HTTP_HOST=127.0.0.1
			- HTTP_PORT={{ .Args.InternalPort }}
		  # the image will be copied over from the original service definition

	templates:
	  inline:
	    # add in a proxy component
	    proxy:
		  image: nginx:1.13.10

    copy:
	  inline:
        # copy a config file into the proxy component's container on startup
	    proxy:
		  /var/conf/nginx.conf: /etc/nginx/conf.d/default.conf

    args:
	  InternalPort: 12000

services:

  site:
    image: rycus86/demo-site
	environment:
	  - HTTP_HOST=0.0.0.0
	  - HTTP_PORT=5000
	ports:
	  - 8080:5000

configs:
  nginx-conf:  # TODO switch to inline config written to a shared volume
    file: ./nginx.conf
```

This stack can be deployed either with `docker-compose` (TODO test both) or into Swarm with `docker stack deploy`. In these cases, you get the original application on its own, listening for incoming requests on port `8080` externally. When you transform this template to use *podlike*, it will run an additional [Nginx](TODO) container in the same network namespace as the app, and configures them so that Swarm routes to Nginx, and Nginx routes to the application on the loopback interface. The internal port its going to listen on now changes to a different one, as configured in the `args` section of the `x-podlike` extension.

I appreciate this doesn't look any better than manually defining the labels for the *podlike* controller, but consider how this would look like with shared templates, when we don't want to inline everything for demonstration purposes:

```yaml
version: '3.5'

x-podlike:
  site:
    pod: templates/pod-with-proxy.yml
    transformer: templates/flask-app.yml
	templates: templates/nginx-proxy.yml
    copy: templates/copy-for-nginx.yml
    args:
	  InternalPort: 12000

services:

  site:
    image: rycus86/demo-site
	environment:
	  - HTTP_HOST=0.0.0.0
	  - HTTP_PORT=5000
	ports:
	  - 8080:5000

configs:
  nginx-conf:  # TODO switch to inline config written to a shared volume
    file: ./nginx.conf
```

OK, that looks a bit better. An additional benefit is that you can easily reuse the same templates for other services in the stack, by referring to the same files. If you have other stacks in different directories, you could still share templates between them by loading them from an HTTP address. And if you're all in with inline templates, check out the [templating docs](TODO) on hints to avoid duplication with YAML anchors.

## Configuration

I tried to make the configuration *pretty* flexible, which means you can define things in a few various ways, whichever works best for you. I'm not going to go into details on everything here and now, but you can look at the [templating documentation](TODO) to see what the options are. Let me just cover the basics and main bits here.

As shown above, the `x-podlike` configuration for each service can have the four template types, each of which can be a single item or a list of them, and all of them are optional. If there is more than one, the results will be merged together in the final output. Refer to the [docs](TODO) to see how the merging logic works. Each item can be given as a template file, an HTTP address for the `http` property, or a *string* with the `inline` key. If the `pod` section is missing, the *controller* is generated with a [default template](TODO), and so does the [main component](TODO) if there are no `transformer` templates given. Both of them also get a lot of properties copied over from the original service definition, like labels, environment variables and such, see the full list in the [source file](https://github.com/rycus86/podlike/blob/master/pkg/template/merge.go) for the merging logic.

Each service can have its own `args` section for any sorts of arguments you can define as a valid YAML mapping, then those will be available for the templates as `{{ .Args.<Key> }}`. The top-level extension field can also have an `args` mapping, and the values from it will be merged with the per-service arguments. These values can be numbers, strings, lists, mappings, or whatever, you'll get them for template rendering in whichever way the Go [YAML package](TODO) I use can parse them.


> TODO note about the volume sharing change

