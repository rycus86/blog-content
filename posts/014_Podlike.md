# Podlike: Emulating Kubernetes pods on Docker Swarm mode

Running co-located containers with shared resources is not a k8s exclusive feature. If your favorite container orchestrator is not *(yet)* Kubernetes, then this post may be of use for you. Let me introduce a new application, [Podlike](https://github.com/rycus86/podlike), that enables *emulated* pods for Swarm mode with Docker.

## Why pods?

Although most pods (TODO link to k8s docs) on Kubernetes are probably configured to run a single container (logically), there are very valid [use-cases](https://kubernetes.io/blog/2015/06/the-distributed-system-toolkit-patterns) to tightly couple multiple ones. Some emerging architectural patterns, namely [sidecars](TODO) and [service meshes](TODO) (TODO plural?), also promote this, and may become the norm rather than the exception in the future. It's no surprise, the benefits are undeniable: you can *decorate* your application with deployment, caching, routing, service discovery logic, custom log collection, etc. without having to hard-wire support for these in the app itself.

> This means, your implementation needs to be concerned by the business logic only.

To me, this is huge. You don't have to distract the application code (and yourself) by integrating a caching framework, or by trying to make sure calls to external endpoints are retried properly, with circuit breaking enabled, and so on. Though frameworks, like [Hystrix](TODO), make these fairly transparent, it still means you have to add them as a dependency to every single application that works in a similar way, as opposed to letting your infrastructure deal with these communication nuances.

Getting a large fleet of existing, *non-container-native* applications deployed in containers with orchestration, will impose a similar challenge. Do you start changing every app to play nice with your log collector, change from responding signals to accept HTTP requests or messages from a queue as triggers, throw in service discovery pings, and untangle your legacy architecture *(read: spaghetti)* straight-away? Or perhaps you leave them as-is, maybe add *minor* changes, and couple them with another application on the infrastructure level, that is proven to work and can be reused across multiple applications?

## Why Swarm?

Let's assume you have played around with Docker, built some images, or pulled them from a registry, and ran them locally. Let's also assume that most people in your team/company/project have done it too. Now you realize, you need to run more of them at the same time for some projects. Your machine has enough resources to do it, so you look into Compose, which operates with very similar settings to the `docker run` command, and it's fairly straightforward to set up the YAML for an app, starting from the command's arguments. All is well, but eventually, you'll just have too many things to keep on a single machine, too many competing Compose projects, etc. It's time for multi-node orchestration! At this point, your Google search reveals, that you should just go with Kubernetes, that's where everyone is heading. But you just need 3 or 5 nodes to run all your apps, to start with at least, and you're already familiar with Compose.

> Going from Compose to Swarm mode is mostly straightforward, and it is very easy!

If you have time and resources to look into Kubernetes, learn the concepts, figure out the best way *for you* to configure the deployment, and convert your existing scripts/pipelines, then you should definitely do it! There's no denying, the ecosystem and the community around Kubernetes is much bigger, advanced configuration or deployment scenarios are probably implemented and published by someone else, so you can leverage that. But if you don't necessarily need all that complexity, do you need to move away from all the Docker tooling you have already familiarized yourself with? No, you don't. You get a pretty good overall package from Swarm too.

- Overlay networking is given, you don't need to bother selecting a network plugin.
- You get a nice, internal DNS resolver to address your services or their tasks.
- You get a pretty good scheduler, with constraints and resource limiting logic.
- You get replicated secrets and configs.
- You get zero-downtime updates and rollbacks.
- Swarm services are *close-ish* to the Compose service concept.
- Most importantly, a large percentage of the configuration for it will be familiar from Compose, or `docker run`.

> In my opinion, the barrier of entry for Swarm is much lower, than it is with k8s.

Now, that the motivation for this application is introduced, let's talk about what it is *so far*!

## The Podlike service

The application itself is written in Go, compiled into a tiny static binary, then packaged as a Docker image, using the `scratch` empty base image. It is intended to be deployed as a Swarm service, although you can run it with Compose or `docker run` too, if you want, for local testing perhaps. Its configuration is driven by the labels on the running container itself, so it lives together with the rest of the stack's description, if you're using stacks.

When scheduled onto a node, Swarm will start a container for the service's task, that will have all the configuration you set when you created (or updated) the service, either through `docker service create`, or by defining them in the stack YAML. Let's call this container the __controller__. On startup, it reads its own container labels from the Docker engine, to prepare the configuration for the other containers in the *"pod"*, let's call them __components__.

> Note: To read the labels, and to manage the components, the application needs access to the Docker daemon on the node it's running on. If this is a no-go in your context, then this app is not for you, sorry.

The components can be defined one-by-one in individual labels, or you can have one label, that points to a Compose file in the container. It's important to note, that only container labels are supported, not service labels, because those are not visible on the container, and service labels can only be accessed on Swarm manager node.

```yaml
version: '3.5'
services:

  my-app:
    image: rycus86/podlike:0.0.1
    labels:
      pod.component.server: |
        image: legacy/app:71.16.5
        environment:
          IT_IS_TWELVE_FACTOR_THOUGH=no

> TODO
```
