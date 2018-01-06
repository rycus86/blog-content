# Home Lab - Swarming servers

This third post in the series explains how I extended my stack to multiple servers with Docker Swarm.

## Quick recap

In the [previous post](TODO), we have brought up a small ARMv8 server running Armbian and installed Docker on it. We also had a look at configuring multiple services on a single box using `docker-compose` and I showed a very simple pipeline for automatically deploying changes and new applications from a version controlled repository where the configuration lives for them.

This works for a handful of applications, but what happens when you need to scale out to multiple servers to have enough resources for all your services?

## Docker Swarm

If you like how you can define configuration for your services with `docker-compose`, you're going to love [Docker Swarm](TODO)! You can use a very similar *YAML* description for the whole stack with additional features for deployment logic and configuration management. The concept of a service is much more emphasised than in Compose. Each service encapsulates a number of tasks that will be scheduled on nodes in the cluster. The orchestration and lifecycle management is all done for you, you just need to take care of the configuration.

Let's start with setting up the servers first. To start with, let's assume we have 3 boxes with the same CPU architecture, running Linux and they all have Docker installed already. Pick one leader and make the other two worker nodes.

> For this post, we'll imagine `amd64` hosts with the IP addresses `192.168.2.1`, `192.168.2.2` and `192.168.2.3`, with the first being the leader.

Log in to the first box and initialize the Swarm.

```shell
$ docker swarm init
<TODO output>
```

This activates *Swarm mode* in the local Docker engine. You can still run standalone containers or use `docker-compose` if you want to, but now you can also create Swarm services. If the host has multiple network interfaces, you may need to add the `--advertise-address 192.168.2.1` flag to the initialization command as well. Get the *join token* from the output of your command and execute it each of the worker nodes. It looks something like this:

```shell
$ docker swarm join xx yy # TODO
<TODO output>
```

Don't worry if you lost the initial output message from the leader, you can get it again by executing `docker swarm join-token worker` on its host. The `join` command registered the new nodes in the cluster and now they are ready to take new tasks and updates. Quickly check that everything is as expected by running this on the leader node:

```shell
$ docker node ls
<TODO output>
```

So far so good, the 3 nodes all show up and one of them is a leader. The [recommendation](TODO) is to have odd number of leaders, because scheduling and cluster management needs concensus through [Raft](TODO) and even numbers of nodes might be split about the current state of things.
