# Home Lab - Open sourcing the stacks

The final post in the series describes the various Swarm stacks I now have in GitHub, and explains the workflows around them.

## Motivation

Until recently, I had a single Swarm stack for all my services in a private [BitBucket](TODO) repository, also containing some of the configuration files for them. I also had sensitive configuration files and secrets at *known locations* on disk, and mounted into the containers that needed them from there. This was working OK for the most (TODO) part, though some services needed a manual *forced* update, when their config has changed. It was also getting hard to manage a single YAML file with *123* (TODO) lines, so I decided, it's time to change things a little bit.

I wanted to make my stack YAML files public, so they could serve as examples for anyone interested. I started splitting the single private repo up to [individual GitHub repositories](https://github.com/rycus86/repositories-TODO-with-query?), where the services are grouped by their different functions in my home lab. Each of them also contains all the necessary configuration for the services within, to make updates easy when any of them changes, thanks to a recently added Docker feature I [wrote about](TODO) previously.

Let's have a look at the stacks to see their services and what they do!

### Web stack

![Web stack](https://github.com/rycus86/home-stack-web/raw/master/stack.png)

The [home-stack-web stack](https://github.com/rycus86/home-stack-web-TODO) is the main entrypoint from external networks. A service, running the [Nginx](http://nginx.org/) [image](TODO) is listening on port 443 for HTTPS connections (TODO drop port 80), and all external HTTPS traffic will go through its instances. This then connects to the other services on an overlay network, called `web`, usually on HTTP.

> Note, that all the other services listen only within the overlay network, they are not (and not need to be) accessible from external networks.

The service uses Swarm configs and secrets for the main Nginx configuration file and for basic authentication configuration, respectively. It also uses a shared volume for the runtime configuration file, where all the upstream servers and the routing rules are defined. This is being kept up-to-date by a pair of [docker-pygen](TODO GitHub) manager/worker services. These react to events from the Docker engine, regenerate the configuration file, then signal the running instances to get it reloaded. I have written a [blog post](https://blog.viktoradam.net/2018/01/20/home-lab-part4-auto-configuration/) about this in more detail, if you're interested. The template for the config generation is also kept in a Swarm config, so the PyGen services can be restarted when it changes.

> The manager service needs to have access to the Docker Swarm APIs, and because of this, it needs to run on a manager node. This is super easy to do with the `node.role == manager` placement constraint.

The tasks started from the Nginx service also have appropriate labels for the [domain automation](TODO blog post link) service to find and signal when the SSL certificates used have been renewed *automatically*, using [Let's Encrypt](TODO) as the provider. The certificate files are stored on a shared volume, so it can easily pick them up from there.

All other services in the `web` stack accept HTTP connections, as described above. These services include this [Ghost blog](https://ghost.org/), my [demo site](https://github.com/rycus86/demo-site), plus a few other [Flask apps](TODO blog post link) for REST endpoints. They all include service labels for routing information, `routing-host` for the domain name I want to expose them on, and the `routing-port` label for the internal port Nginx can connect to them. Some of them also use Swarm secrets for various settings, like API keys for external services. Most of them are attached to the `monitoring` overlay network too, so that Prometheus can also connect to them to scrape their metrics. *(see below)*

### Monitoring

![Monitoring stack](https://github.com/rycus86/home-stack-monitoring/raw/master/stack.png)

At the heart of this stack, there is a [Prometheus](TODO prom.io) instance running, that scrapes other services, and collects their metrics. Its configuration is kept up-to-date by another set of PyGen services, the configuration file being stored on a shared volume again. The other services only need to be on the `monitoring` network, and define the `prometheus-job` and `prometheus-port` service labels to get automatically registered. I have another [blog post](https://blog.viktoradam.net/2018/02/06/home-lab-part5-monitoring-madness/) describing this in more detail.

Beside the application-level metrics, *physical* node metrics are coming from a [Prometheus node exporter](https://github.com/prometheus/node_exporter) instance: CPU, memory and disk usage, for example. I'm also collecting container-level metrics, using [Telegraf](https://github.com/influxdata/telegraf), that gives a more detailed view on how much CPU, memory or network bandwidth do the individual containers use. Both of these are running as *global* services, meaning they will get an instance scheduled to each node in the Swarm cluster.

All these metrics are then visualized by a [Grafana](https://grafana.com/) instance, that provides beautiful dashboards, with the data provided by querying Prometheus. The main Grafana configuration is also coming from a Swarm secret, stored in an encrypted file inside the same GitHub repository. *(more on this later)*

The stack also includes a [Portainer](https://portainer.io/) instance to have a quick view of the state of the containers and services. This service does not connect to the `web` network, since I don't want it publicly available, instead it publishes a port on the Swarm *ingress* network. This allows me to access it from local network at home, without exposing it on the internet.

### Logging

![Logging stack](https://github.com/rycus86/home-stack-logging/raw/master/stack.png)

As described in a [previous post (TODO anchor?)](https://blog.viktoradam.net/2018/02/06/home-lab-part5-monitoring-madness/), this stack contains an [Elasticsearch](https://www.elastic.co/products/elasticsearch) instance for log storage and querying, [Kibana](https://www.elastic.co/products/kibana) for visualization, and [Fluentd](https://www.fluentd.org/) for log collection and forwarding.

The Fluentd instance publishes its port onto the *ingress* network, and (almost) all services will use the `fluentd` Docker logging driver to send their logs to it. The reason for this is that the logs are sent from the Docker engine, on the physical network, rather then on an internal overlay network. Each service defines a logging `tag` for itself, so their logs can be easily found in Kibana later.

The logging-related services themselves, plus a few other *chatty* ones, don't use Fluentd. They kept the default `json-file` log driver, with some configuration for log rotation to avoid generating huge files on the backing nodes' disks.

All the Elasticsearch and Fluentd configuration files are kept in files [in the GitHub repo](TODO link to ./config), and they are then used as the data for the Swarm configs generated for their services. 

### Webhooks

![Webhook stack](https://github.com/rycus86/home-stack-webhooks/raw/master/stack.png)

All the updates to all my Swarm stacks are managed by webhooks, processed using my [webhook Proxy](https://github.com/rycus86/webhook-proxy) app. You can find some information on how in a [previous post](https://blog.viktoradam.net/2018/01/13/home-lab-part3-swarm-cluster/), though it's fairly straightforward.

There are two services of the same app. The externally available `receiver` takes the incoming webhooks as HTTP requests through Nginx, validates it, then forwards it to the internal `updater` instance. Only the first one needs to be on the `web` network, so that Nginx can talk to it, the other one is only accessible from the stack's default overlay network.

### Other stacks - Docker + DNS + private

> TODO link to the 009 post

## Update workflows

> TODO update workflow - maybe above at the webhooks?

## Sensitive configuration

> TODO git-crypt

## Swarm networks

> TODO about migrating between legacy and new networks

## Final words

> TODO links
