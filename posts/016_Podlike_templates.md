We've seen that we can run co-located and coupled services on Docker Swarm. This post shows you how to use templates to extend your services in a common way.

If you haven't already done so, check out the [introduction post](https://blog.viktoradam.net/2018/05/14/podlike/) and the [examples](https://blog.viktoradam.net/2018/05/24/podlike-example-use-cases/) to see what [Podlike](https://github.com/rycus86/podlike) can be used for. In short, you can get a set of containers to always run on the same node in Docker Swarm mode as a task of a service. These containers will share a network namespace, so it makes it very easy to run [sidecars](https://docs.microsoft.com/en-us/azure/architecture/patterns/sidecar) for example. You can also share PID namespaces and volumes, that enables using different patterns for coupled applications.

## The problem

While I was working on the [demo examples](https://github.com/rycus86/podlike/tree/master/examples), one thing became clear to me. If you have homogeneous applications, and you always want to *decorate* them with the same components, then there can be an awful lot of duplication in stack YAML pretty quickly. In the [biggest stack](https://github.com/rycus86/podlike/blob/master/examples/modernized/stack.yml), each of the applications we want to run in a [service mesh](https://www.thoughtworks.com/radar/techniques/service-mesh) is coupled with the same: a [Traefik](https://traefik.io/) reverse proxy, a [Consul](https://www.consul.io/) agent for service discovery support, a [Jaeger](https://www.jaegertracing.io/) agent for distributed tracing, and a [Fluent Bit](https://fluentbit.io/) instance for centralized logging.

Their configuration is almost identical for each service, with the exception of service names and log file paths. Do we really have to duplicate their definitions then? Surely, there's a better way.

## Templates to the rescue

We have identified that the component configurations really only differ in a few variables, but the rest of it could easily be templated. Why not do exactly that then?

In version `0.3.0` of the app, I've added support for transforming a set of [Compose files](https://docs.docker.com/compose/compose-file/) into a single YAML, that changes the services you want into *"pods"*, while still being compatible with the format `docker stack deploy` expects. Actually, with the help of [extension fields](https://docs.docker.com/compose/compose-file/#extension-fields), you can decide whether you want to deploy the stack as-is, or the templated version with the coupled components in it. This could be useful, if you don't necessarily need all those extra bits for local development, but would want to have them on the target servers or environment.

> Top-level extension fields are supported on Compose schema version 3.4 and above.

You can have a *top-level* extension field, called `x-podlike`, that can define 4 types of templates for each individual service:

1. `pod` that generates the result Swarm service definition
2. `transformer` to generate the configuration for the main component
3. `templates` to produce any additional components
4. `copy` for generating the configuration for the files to copy into the component containers



> TODO note about the volume sharing change
