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
Swarm initialized: current node (jbrvijh5o4ae9gss5u3st2p45) is now a manager.

To add a worker to this swarm, run the following command:

    docker swarm join --token SWMTKN-1-36p88rlrr6aqf64fdrvknnphs803sea9k8ia7ygkcz5d29m129-894eqkdgadkr3ebnhprv0hmpt 192.168.2.1:2377

To add a manager to this swarm, run 'docker swarm join-token manager' and follow the instructions.
```

This activates *Swarm mode* in the local Docker engine. You can still run standalone containers or use `docker-compose` if you want to, but now you can also create Swarm services. If the host has multiple network interfaces, you may need to add the `--advertise-address 192.168.2.1` flag to the initialization command as well. Get the *join token* from the output of your command and execute it each of the worker nodes. It looks something like this:

```shell
$ docker swarm join --token SWMTKN-1-36p88rlrr6aqf64fdrvknnphs803sea9k8ia7ygkcz5d29m129-894eqkdgadkr3ebnhprv0hmpt 192.168.2.1:2377
This node joined a swarm as a worker.
```

Don't worry if you lost the initial output message from the leader, you can get it again by executing `docker swarm join-token worker` on its host. The `join` command registered the new nodes in the cluster and now they are ready to take new tasks and updates. Quickly check that everything is as expected by running this on the leader node:

```shell
$ docker node ls
ID                            HOSTNAME            STATUS              AVAILABILITY        MANAGER STATUS
jbrvijh5o4ae9gss5u3st2p45 *   leader              Ready               Active              Leader
jtlbeh4u0c4krega1u2agyifh     worker-1            Ready               Active              
ffkef7x4l1njjxeinxqy6zwwd     worker-2            Ready               Active              
```

So far so good, the 3 nodes all show up and one of them is a leader. The [recommendation](TODO) is to have odd number of leaders, because scheduling and cluster management needs concensus through [Raft](TODO) and even numbers of leaders might be split about the current state of things.

## Deploying stacks

If you're familiar with `docker-compose` already, then deploying a group of services as a *Swarm stack* will feel very similar. You can use the same *YAML* format to describe the services, their settings and configuration. Let's look at an example!

```yaml
version: '3'
services:

  traefik:
    image: traefik
    command: >
      --web -c /dev/null
      --docker --docker.swarmmode --docker.domain=docker.localhost
      --logLevel=DEBUG --accessLog
    deploy:
      placement:
        constraints:
          - node.role == manager
    labels:
      - 'traefik.enable=false'
    networks:
      - apps
    ports:
      - '80:80'
      - '8080:8080'
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /dev/null:/etc/traefik/traefik.toml

  ping:
    image: python:3-alpine
    command: |
      python -c "
      import socket
      from http.server import HTTPServer, BaseHTTPRequestHandler

      class Handler(BaseHTTPRequestHandler):
          def do_GET(self):
              self.send_response(200)
              self.end_headers()
              self.wfile.write(bytes('Pong from %s\\n' % socket.gethostname(), 'utf8'))

      HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
      "
    networks:
      - apps
    deploy:
      mode: global
      labels:
        - 'traefik.port=8080'
        - 'traefik.docker.network=demo_apps'
        - 'traefik.frontend.rule=PathPrefixStrip: /ping'

  hello:
    image: python:3-alpine
    command: |
      python -c "
      import socket
      from http.server import HTTPServer, BaseHTTPRequestHandler

      class Handler(BaseHTTPRequestHandler):
          def do_GET(self):
              name = self.path.split('/')[-1].capitalize()
              self.send_response(200)
              self.end_headers()
              self.wfile.write(bytes(
                  'Hello, %s! (from %s)\\n' % (name, socket.gethostname()), 'utf8'
              ))

      HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
      "
    labels:
      - traefik.port=8080
      - traefik.docker.network=demo_apps
      - "traefik.frontend.rule=PathPrefixStrip: /hello/"
    networks:
      - apps
    deploy:
      replicas: 2
      labels:
        - 'traefik.port=8080'
        - 'traefik.docker.network=demo_apps'
        - 'traefik.frontend.rule=PathPrefixStrip: /hello/'

networks:
  apps:
```

We have a few things going on in here, let's start with the Python services. They are both simple HTTP servers that respond to *GET* requests with a fixed message and their hostname.

> I [love](TODO Flask post) how simple but powerful Python is. Using only standard libraries we have a simple HTTP endpoint in about 15 lines. Just awesome!

Sure, this is not a production-ready server or production-quality code, but I find it amazing how easy it is to code something like this up in Python for demonstration purposes for example. *Anyways*, back to our stack!

The third service is an awesome, modern reverse proxy, called [Traefik](TODO), which was built with dynamic backends in mind from the start. It makes it perfect for routing traffic to services running in containers that may come and go all the time when their configuration changes for example. Traefik is super powerful and there are lots of nice things built into it (like HTTP/2 support, automatic SSL with [Let's Encrypt](TODO), metrics support, etc.), but for this post it's enough to know that it can read state information from Docker and adjust its routing configuration automatically based on metadata.

> Make sure to check out their excellent [documentation](TODO) if you'd like to know more about Traefik!

In our example, requests to `/hello/<name>` will be handled by the `hello` service and requests to `/ping` will be served by tasks of the `ping` service. This is configured for Traefik through the `traefik.frontend.rule` labels defined in the *YAML* file. It is time to deploy our stack now! Save the above as `docker-compose.yml` and execute:

```shell
$ docker stack deploy demo -c stack.yml
Creating network demo_apps
Creating service demo_hello
Creating service demo_traefik
Creating service demo_ping
```

The command above has created the services and the new `overlay` network (`demo_apps`) for them.

> Services in Swarm stacks are prefixed with the name of the stack. Some configuration will need this (`demo_` in our example).

Let's check the status of the services. Eventually it should look like this:

```shell
ID                  NAME                MODE                REPLICAS            IMAGE               PORTS
b216o19ezj6v        demo_hello          replicated          2/2                 python:3-alpine     
kjoq3qy9ahqu        demo_ping           global              3/3                 python:3-alpine     
dk0d1lcv98l5        demo_traefik        replicated          1/1                 traefik:latest      *:80->80/tcp,*:8080->8080/tcp
```

All containers started by the tasks will be attached to this network where they can talk to each other using service names as hostnames, even if they are running on different physical hosts, *pretty cool!* [Overlay networks](TODO) are neat, check out the documentation on the link if you're interested to know more about them. The containers also get their own unique IP addresses on this network and as they start up, Traefik will add routing to them using these addresses. You can see this on a nice dashboard at the `http://localhost:8080/dashboard/` URL.

    TODO Image of the dashboard

Let's try hitting our services with a few request! You should get something like this:

```shell
$ for i in {1..5}; do curl -s http://localhost/ping ; done
Pong from 17ddc60169df
Pong from f2980ab861d8
Pong from 7d3bf269a621
Pong from 17ddc60169df
Pong from f2980ab861d8
$ curl -s http://localhost/hello/world
Hello, World! (from abe7c17b92bc)
$ curl -s http://localhost/hello/viktor
Hello, Viktor! (from 407237d6b729)
```

You can see that the requests were distributed across different instances of our services. `ping` was configured as a `global` service, meaning it has one tasks scheduled for every node in the cluster, while `hello` has two replicas scheduled to any of the nodes. You can see where they are exactly using the `docker stack ps` command.

```shell
$ docker stack ps demo
ID                  NAME                                  IMAGE               NODE                DESIRED STATE       CURRENT STATE                ERROR               PORTS
0zc2187tfqyq        demo_ping.ffkef7x4l1njjxeinxqy6zwwd   python:3-alpine     worker-2            Running             Running about a minute ago                       
t122jxe4bu2m        demo_ping.jtlbeh4u0c4krega1u2agyifh   python:3-alpine     worker-1            Running             Running about a minute ago                       
n1rz8qs7e37q        demo_ping.jbrvijh5o4ae9gss5u3st2p45   python:3-alpine     leader              Running             Running about a minute ago                       
phvk48hy6h5b        demo_traefik.1                        traefik:latest      leader              Running             Running about a minute ago                       
dez933di9o4m        demo_hello.1                          python:3-alpine     worker-1            Running             Running about a minute ago                       
kclnyekyym5e        demo_hello.2                          python:3-alpine     leader              Running             Running about a minute ago                       
```

You can also notice that the Traefik container is always running on the leader node. This is dome by the *constraints* defined on the service and is necessary, so that it has access to the tasks information using the Docker API. It also needs a connection to it, this is why it has the `/var/run/docker.sock` *bind-mounted* to it.

## Sharing is caring?

If you used `docker-compose`, you know how easy it is to share files or folders from your host with the containers. When running tasks spanning multiple nodes in the Swarm cluster, things could get a *little bit* trickier.

Let's get our *YAML* file a bit cleaner by extracting the inline Python code into its own file and mounting it back to the services.
