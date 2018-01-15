# Home Lab - Configuring the cattle

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

The [worker image](TODO) shares the codebase with the main tool but it doesn't generate templates. It's purpose is to listen for Docker events on __all nodes__ in the Swarm cluster and forward them to the manager instance. They can also execute actions, received from the manager, that are only available to target containers running on the same node. Restarts for example can be executed on the Swarm service level with `docker service update <service> --force` but signals can only be sent to individual containers which are not necessarily running on the manager's node.

This is why the `worker` is a `global` service that will have an instance running in every node in he cluster. The manager instance has to run on a Swarm manager node so it can access the Swarm APIs, which are not available to the worker nodes.

```shell
$ docker service ls
TODO failing output from worker
```

## SSL and certificates

I want my services to only expose secure endpoints to the internet. For this reason, all of them are HTTPS enabled and HTTP requests are simply redirected to the HTTPS variant.

To get SSL certificates, I use [certbot](TODO) from the awesome people of [Let's Encrypt](TODO).Their missions is (TODO), which is very noble, and for this reason, they provide __free__ certificates that are valid for 3 months. Before they expire you can easily renew them using *certbot*. This is how I do it.

I have a Debian based (TODO?) Docker image that has the `certbot` tool installed. Once every 12 hours, it checks all my subdomains to see if their certificate is due for a renewal. It is done as a simple, parameterized command executed in the container, not wrapped in another tool (yet). The main process is basically an infinite loop with `sleep` and it has signal support to start the renewal immediately when I want it to pick up a new domain quickly. Not very fancy, I know, but it gets the job done.

The actual renewal process is done by serving up a static file over HTTP on the new domain. This is really the only area that is accessible on port 80. The request will come in as `http://your.domain.com/.well-known/acme/ TODO` and the content it expects comes from certbot.

> There other ways to verify that you own a domain which might be simpler for your use-case. Check out the [documentation](TODO) to see those.

Assuming the domain is already set up and is pointing to your *origin* server, this process should be fairly straightforward. `certbot` allows you to define hooks for the setup and cleanup steps (TODO others?), for me, these look like this:

```
TODO setup and cleanup
```

The `auth-hook.sh (TODO)` takes the configuration parameters (TODO) and saves them in a location where Nginx can access them. The `cleanup.sh (TODO)` is basically just removing these. The actual `cerbot` invocation is in a *Bash* script, generated by *PyGen*.

```
TODO template
```

The email address I've registered with Let's Encrypt is defined in a Docker service label. The list of domain names also comes from labels, which are attached to the services that they belong to. When I want to set up a new one using a new subdomain, I just need to define it in the stack *YAML* with the appropriate labels and the *rest is magic*!

The last piece of the puzzle is in the Nginx configuration. The `location` blocks contain lines like these:

```
TODO nginx SSL config block
```

To be honest, I *still have a few manual steps* to do in this workflow, one of them is to register the new subdomain on my DNS provider. This is how I'm planning to automate it *soon*.

## Domain registration

I've originally bought `viktoradam.net` from [Namecheap](TODO). After a while, I've found myself in need of a [CDN](TODO), so I signed up for [Cloudflare](TODO) and transferred the DNS setup there. Every time I add a new subdomain, it needs to be registered on their system.

Cloudflare has pretty nice [API](TODO) and even a ready-to-use [Python SDK](TODO) for it. My first option is to have a service running in my stack that picks up new domain names from the other services' labels and registers them using the API if it's missing. This would be very similar to the *certbot* workflow. I *might* run into some timing issues though as a new DNS entry needs a couple of seconds or minutes to come alive, so it might not be ready in time for the Let's Encrypt domain validation request.

My second option is to reduce how much I have to do manually. I'm using a free [Slack](TODO) account with some automation already. Slack supports [chatbots](TODO) and there are even [Python modules](TODO) for them that look promising. I could write a bot, to which I could tell about a new subdomain I want registered, and it would do it for me. *Less clicking around!*

I might end up using something different when I het around to actually do it, but right now, these two options seem viable to me.

## Dynamic DNS

I host my services on my home network with a simple internet subscription. My provider doesn't guarantee a fixed IP address, so whenever it changes, I need to tell Cloudflare about the new one. This is pretty simple and a very common problem, therefore there is a tool to do this for me.

[ddclient](TODO) has been around since (TODO year) and it's proven very useful for many people. To keep things portable, I run it as a service in a Docker container using my *multi-arch* [image](TODO). All it does is, it wraps the `ddclient` tool, so the parameters are the exact same. It needs a configuration file to describe the provider, access keys and the list of domains. This can easily be templated like this:

```
TODO ddclient template
```

Once I have this file generated, I can use it in my stack. Whenever the configuration changes, I need to restart the container to pick up the changes.

```yaml
TODO stack.yml with ddclient + docker-pygen + workers
```

### Monitoring configuration

I use [Prometheus](TODO) to collect metrics from my services and servers. It is a brilliant, pull-based collector (TODO what's the term?) that can scrape target systems and efficiently store the time-series data for their metrics and the changes of those.

> You can read more about Prometheus in the next part of the [series](TODO), that is about monitoring and logging.

The scrape targets are defined in *YAML* file. Prometheus supports [many](TODO) *service discovery* methods to collect the actual endpoints, one of them is `dns_sd_config (TODO)` that can list the IP addresses of services behind a common DNS name. This plays nicely with Swarm networking, that includes an internal DNS resolver for reasons exactly like this.

```shell
# inside a container within a Swarm stack
<TODO>
$ nslookup service
TODO
$ nslookup tasks.service
TODO
$ for i in $(seq 3); do host service; done
TODO show the DNSRR
```

The Prometheus configuration file can be easily templated as well. When it changes, it can be *hot-reloaded* by sending a `HUP` signal to the main process. The template I use scrapes the Docker engine metrics from all the nodes in the cluster, plus all the services that have labels describing their metrics endpoints.

```
TODO prometheus template
```

To put it all together, this is how this automation looks like in my stack:

```yaml
TODO prom + pygen + worker + node-exporter
```

## What's next?

It feels like, there is always one more thing to automate. Whenever it gets uncomfortable or cumbersome to change some configuration or to set something up, I'm trying to find a way to automate it, so I wouldn't have to bother with it again. (TODO a bit more?)

Once most of our configuration is taken care care of automatically, it's good to know if it does *actually* work. The next post will go over all the monitoring and logging systems I have in my stack.

The [series](https://blog.viktoradam.net/tag/home-lab/) has these parts so far:

1. [Home Lab - Overview](https://blog.viktoradam.net/2018/01/03/home-lab-part1-overview/)
2. [Home Lab - Setting up for Docker](https://blog.viktoradam.net/2018/01/05/home-lab-part-2-docker-setup/)
3. [Home Lab - Swarming servers](https://blog.viktoradam.net/2018/01/13/home-lab-part3-swarm-cluster/)
4. *Home Lab - Configuring the cattle*
