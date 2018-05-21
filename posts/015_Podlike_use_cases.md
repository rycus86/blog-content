# Podlike: example use-cases

If we can run co-located containers on Docker Swarm mode, what can we use them for? This post goes through a few made-up example stacks, and explains the setup and configuration of the components within the sort-of pods.

Hopefully, you've read the [previous post](TODO), which introduced [Podlike](https://github.com/rycus86/podlike), an application that attempts to emulate some of the features you'd get from a Kubernetes [pod](TODO docs), implemented for Docker containers managed by Swarm mode. In the intro, I've tried to explain the concepts and the design behind it, but haven't showed any concrete examples for use-cases I think *"pods"* can be useful, so I'll do it in this post. We're going to start with smaller examples, focusing on one or two features you get from tightly coupled containers, then we're off to deeper waters with larger, and sadly, more complex stacks.

The applications are small Python web servers or standalone programs in most cases, that only serve demonstration purposes, they're not implemented to have any usefulness (TODO spelling) or value really. What I'm focusing on, is what can you get from external components carrying logic you can avoid adding to the application itself, and what are the minimal changes to the app if any. Most of the examples, if not all of them, can be implemented in different ways that would probably make more sense, I'll try to call them out, so take these as an alternative option for running multiple services that need to work together in some ways.

The use-cases we're going to look at are: (TODO anchors for the items in the list)

1. Sidecars
2. Log collectors
3. Notifications with UNIX signals
4. Shared volumes for configuration
5. HTTP Health-checks for non-HTTP apps
6. Service meshes
7. Modernizing a stack without changing the applications too much

It's a lot to cover, so let's get started!

## Sidecar

> TODO is a diagram an overkill here?

The first example takes an existing [Flask](TODO) application, that is running behind [demo.viktoradam.net](https://demo.viktoradam.net), and adds caching and *serve-stale-on-error* functionality using an [Nginx](TODO) reverse proxy in front of it. The application itself doesn't need to support these at all, no code changes are required, and adding retry logic, circuit breaking, etc. would be just as easy.

> Try the [sidecar example](https://github.com/rycus86/podlike/tree/master/examples/sidecar) by following the instructions in README!

A nice side-effect of this setup, is that the application can listen on `127.0.0.1` only, because of network namespace sharing, so you can put something in front of it, that might be more secure than the application or the framework it uses. Also, the network packets [shouldn't leave](TODO docs?) the container this way, so some network traffic is saved here, if that's a factor.

An alternative to this on Swarm could be simply placing the application and the sidecar on the same *overlay* network, and point the proxy to the app container's address. The services would scale individually in this case, and it could also mean relying on some form of service discovery to find the backend addresses to load-balance between from each of the frontend servers.

## Log collector

> TODO diagram
> TODO change to fluent-bit for tailing the logs

Let's assume for this example, that we have an existing application with it's own well-tested way of writing logs, and we're not quite ready to give up on it. By sharing a volume with the application and with something that picks up those logs, we don't need to. The app can continue whatever it was doing so far, and an external service can take care of this.

> Have a look at the [log collector example](https://github.com/rycus86/podlike/tree/master/examples/logging) in the project!

The application in the example is configured to write in a log file that happens to sit on the shared volume, and the [fluentbit](TODO spelling + link) instance will simply *tail* them from there to the standard output. It could also just as easily forward them to a central log aggregator.

The *not-so-nice* thing to note here, is that all volumes are shared between all the components, and this __also includes__ the Docker daemon's API socket, so the apps could get dangerous with it. This is likely to change in the future, but for now it is like this, just be aware.

An alternative here could be running a log forwarder agent on each Swarm node, that is preconfigured to look for log files in a specific folder, and the app service would point a *mount* to this same folder. This assumes individual configuration on the application and the log forwarder agent, plus the chosen path should exist, and the filenames should be distinct to avoid one service trying to write another one's logs files.

> TODO change the log volumes to individual ones for the modernized example

## Sending UNIX signals

> TODO diagram

Some applications respond to certain triggers coming from UNIX signals. It is quite common to get the app to reload its configuration when it receives a `SIGHUP` signal, *Nginx* and [Prometheus](TODO) both do this for example. The example is demonstrating a similar, but much simpler implementation.

> See the [signal example](https://github.com/rycus86/podlike/tree/master/examples/signal) on GitHub!

One application writes its own PID to a shared volume, then waits for `SIGHUP` signals, and prints a *hello* message when it received one. The second component reads the PID file, and periodically sends a signal to the target process. They can do so, because they use a shared PID namespace, normally containers would only see PIDs started from their own main process.

Replicating this with two Docker containers on the same host is doable with `docker kill -s HUP <target>`, but it is somewhat difficult on Swarm if they end up on different nodes. Have a look at a [cumbersome implementation](TODO domain-automation signal sending) I did for an application that needs to signal other containers not necessarily running on the same host. Alternatively, the applications could change to accept triggers in different ways, by accepting an HTTP request, or receiving an event on an event bus (TODO term) like [Nats](TODO link + .io?) for example.

## Shared volumes

> TODO diagram

Building on the previous two examples, the next one demonstrates how a simple application could control another one by changing its configuration and triggering a reload on it. For example, we could implement a basic *CD pipeline* that would fetch a web server's configuration from *Git*, and get it activated by sending a UNIX signal to its process.

> Check out a simple implementation of this with a [shared volume](https://github.com/rycus86/podlike/tree/master/examples/volume)!

The example in the project repository has a simple Python server that can regenerate an *Nginx* configuration for the server running in the same *"pod"*, then it sends a `SIGHUP` to it to get the new config applied.

As an alternative, you could use a web server or reverse proxy here, that can dynamically change and reload its own configuration, based on service discovery perhaps, like [Traefik](TODO) or [Envoy](TODO) would do for example.

## Health-checks

In this example, we take a Java application that we've grown to love in whatever state it's in, and wouldn't change it for anything. It writes some very important reports to disk, and exports (TODO term) a JMX bean that can tell us if it's made any progress in the last 5 seconds. Now we decide to run this app on our existing Swarm cluster, and we want to hook it up to our HTTP ping based liveness checking infrastructure.

> TODO

## Service mesh

## Modernized stack

