# Home lab - Overview

This post is the first in a series explaining the setup I use to run my websites and their related services at home on cheap hardware using containers.

## Background

I spend a lot of time working on my home lab, *perhaps too much*, but I enjoy it a lot. I always wanted to have some public-facing websites and endpoints I can play with or share with everyone. I also wanted being able to update these as easily as possible, meaning that after finishing with coding up a new change I don't want to spend a lot of time getting the application deployed manually. I also didn't want to spend a lot of money on something I'm working on in my free time.

To list out my *"requirements"* for the Home lab:

- Update automatically on code changes
- Update automatically on configuration changes
- Be easy to scale and expand
- Be cheap

I have started off with a single [Pine64](https://www.pine64.org/?page_id=1194) server having 2 GB memory in total running maybe 4 or 5 containers. As of this writing, the stack now has 3 servers hosting over 30 containers... *Yes, it blew up a little.*

## Physical servers

The current setup has 2 [Pine64](https://www.pine64.org/?page_id=1194) instances and a [Rock64](https://www.pine64.org/?page_id=7147) from the same manufacturer. They are all 64-bits ARM servers around the size of a [Raspberry Pi](TODO link). In total I now have 12 CPU cores with 7 GB of memory to host all the services I'm running. They are great little computers for around (TODO insert price) per instane.

You can run a few different flavors of Linux on them. I've opted to use [Armbian](TODO link) that gives me a Ubuntu derivative. This is particularly important for Docker which only has official support for Ubuntu on the *arm64/aarch64* architecture. This means that installing and upgrading Docker is as simple as:

```bash
$ curl -fsSL get.docker.com | sudo sh
```

The performance seems OK for the applications I'm using them for. When available memory starts getting a bit low, I can just order one more instance and add it to the cluster. Last time it took about 30 minutes including downloading the base image and writing it to an SD card.

## Clustering

I want my services to use all of the available servers. I don't particularly care about maximizing the usage on them, only that the applications are distributed accross them in a sensible manner. I also wanted to avoid hard-coding IP addresses for service endpoints and pinning them to specific servers to keep things dynamic and portable. For this use case, [Docker](https://www.docker.com) and [Swarm](TODO link) [stacks](TODO link) are doing an awesome job!

Having everything packaged as Docker images and running them as containers makes the applications portable. I even build them for multiple processor architectures (`amd64`, `arm` and `arm64`) so I can run them on a Raspberry Pi or an x86 NUC (TODO?) in the future if I decide to. Docker also gives me a unified way of deploying applications regardless of what programming language are they in or what dependencies do they need.

Docker Swarm takes care of the clustering logic. One node is the `leader` and joining new nodes is as easy as:

```bash
$ docker swarm join <TODO example>
```
