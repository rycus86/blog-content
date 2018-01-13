# Home Lab - Configuring cattle

Let me explain the configuration method I use for my services and HTTP endpoints. *Spoiler:* it's Docker and it's automated.

## So far...

In the previous posts of the [series](TODO) I walked you through how I've set up my home lab with ARMv8 servers and `docker-compose` and how it's changed to Swarm.

While I only had an [Nginx](TODO) and maybe 3 [Flask](TODO) services in the stack, I could have just used some hard-coded configuration (I didn't) to get them to work together. Even for small stacks though, it makes complete sense to let the system describe and configure what it needs to, leaving you with time to spend on more important things instead, like developing your apps and tools, not fiddling with config files all the time.

## Templates

OK, so I don't want to deal with configuration files, but I kind of have to, right? Unfortunately.

If I do have to write a config file once though then I can just take a bit of extra time and care to create it as a template so I don't have to touch it the next time something changes in the system. If I'm lucky.

There are quite a few templating languages and frameworks around, [Go templates](TODO) seem to be quite popular these days for example. You can even find systems that use templates to auto-generate configuration for you based on current state read from an underlying system, (TODO examples). If you want to go further, there are others that can run actions when the configuration is updated, reloading [HA-Proxy](TODO) for example with [SmartStack](TODO) or (TODO consul). Then there are systems which can tap into your existing services to generate their own configuration periodically or on changes and reload their internal logic or routing, [Traefik](TODO) for example (TODO others?).

> I sort of like doing things the hard way, so naturally, I wrote my own configuration generator tool: [docker-pygen](TODO).

It's nothing special really, it was just the most convenient for me at the time. It's written in Python and it's using [Jinja2](TODO) templates which I was already familiar with through [Flask](TODO) and it uses the [Docker API](TODO) through the [docker-py](TODO) SDK to listen for events and read current state. It was heavily inspired by [docker-gen](TODO) from [jwilder](TODO) but I really didn't want to start using Go-templates and it didn't support Swarm.

With running the [docker-pygen container](TODO) in the stack and giving it access to the Docker daemon, it can listen for select Docker events and evaluate it's template with the Docker service, task, container and node information available as variables to it. If the target file changes, it can also execute an action, like sending a signal to a container or restarting one.

Some of the information I need in my templates really are dynamic that change all the time, like IP addresses of the containers for example. Some of it though is static and will always stay the same for a service. For example, the domain its endpoint is exposed on or the internal port number to forward requests to, etc. For these metadata I'm using Docker [service labels](TODO) in the stack *YAML*, so it's all in code and checked into version control.

## Reverse proxy config

I've mentioned in previous posts that I'm an Nginx fan, I think it's just awesome. Nginx doesn't do dynamic backends though, in the open-source community version at least, so every time a new container starts or stops, it needs to be updated in the Nginx configuration file and the main (TODO master?) needs to be reloaded. This can be done with sending a `HUP` signal to the process. If you use the [official Nginx library image](TODO) then you can send a reload signal with `docker kill -s HUP <nginx-container>` that will be forwarded to the main process (`pid 1`) in the container.

You can have a look at a working template in [this GitHub repo](TODO) as an example. Let me explain the main bits here too.

```
# included from the root /etc/nginx/nginx.conf as
# include /etc/nginx/conf.d/default.conf
TODO nginx config template
```

This example generates one [upstream](TODO) per domain + [URI](TODO) prefix and lists the IP addresses of all the running tasks for a service responsible for dealing with requests on these [URLs](TODO). If you're using Docker [health-checks](TODO), and you should, then it will filter out the ones that are running but unhealthy, because of the `.healthy(..)` (TODO) filter in the template.

```
... cont
TODO nginx config for the server+location
```

Here we're just mapping the `upstreams` to domains and `locations`. I use common settings for everything that makes sense for *my* systems and allow overriding some from labels, for example max upload size or basic authentication.

Notice that the configuration doesn't refer to any of the services or tasks explicitly. It doesn't have special cases or one-off extras for some of them. Everything is treated the same and the behaviour can be altered through runtime metadata attached to the containers.

The *PyGen* service is using a similar configuration to this:

```yaml
TODO pygen + worker
```

I use a template file that is also checked into version control and I get it to signal the `nginx` service to reload the configuration when something changes. The `--interval` argument allows for batching the signal actions so that even if the state changes 20 times in 1 second, we'll only reload the Nginx configuration once.

The [worker image](TODO) shares the codebase with the main tool but it doesn't generate templates. It's purpose is to listen for Docker events on __all nodes__ in the Swarm cluster and forward them to the manager instance. They can also execute actions, received from the manager, that are only available to target containers running on the same node. Restarts for example can be executed on the Swarm service level with `docker service update <service> --force` but signals can only be sent to individual containers which are not necessarily run on the manager's node.

This is why the `worker` is a `global` service that will have an instance running in every node in he cluster. The manager instance has to run on a Swarm manager node so it can access the Swarm APIs, which are not available to the worker nodes.

```shell
$ docker service ls
TODO failing output from worker
```

## SSL and certificates

nginx config
certbot config

---
Nginx
LetsEncrypt
Ddclient
Prometheus
--Cloudflare
