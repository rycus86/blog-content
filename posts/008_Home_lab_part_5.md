# Home Lab - Monitoring madness

Having looked at the configuration and setup of the services in the Home Lab, it's time to talk about how we can monitor them and manage their logs.

To recap quickly, the stack consists of a couple [Flask](TODO) webapps behind an [Nginx](TODO) reverse proxy, a pair of [webhook processors](TODO) and lot of [configuration generators](TODO). There are a couple more bits and pieces, like a [DynDNS client](TODO) and a private [Docker Registry](TODO), but the point is that there are more apps than one could comfortably monitor manually over an SSH session.

## Logging

Let's start with the log collection first. In Docker, most applications would log to the standard output and error streams. The Docker engine can then collect these messages coming out of the containers. By default, it stores them in files in *JSON* format. It also supports a bunch of [logging drivers](TODO) if you want something more flexible or robust.

I wanted an open-source solution for collecting, storing and visualizing logs so, obviously, I opted for a modified *ELK* stack. [Elasticsearch](TODO) stores and indexes the log messages, then [Kibana](TODO) can provide a pretty nice UI for them. For the third part, instead of using [Logstash](TODO), I chose to have [Fluentd](TODO) collecting the logs and forwarding them into *Elasticsearch*. It is an awesome [CNCF](TODO) project (TODO or just landscape?) and it has a slightly smaller memory-footprint than *Logstash*, which is important for me, running the whole stack on a set of *ARM64* servers with little memory available.

On that note, *Elasticsearch* can also be quite memory-hungry. I've tried a few different settings, and the lowest I could get was 600 MB memory. With anything under that, the app either doesn't start, or crashes during startup. Another thing I learned the *hard way* is that the *Elasticsearch* server needs more CPU as the search index grows. After having it in place for about a month and a half, the app generated *40x load* on the server, making it almost completely unusable. After magically regaining control over it, I deleted about 30 days worth of data, starting from the oldest, and it put back the CPU usage to around *30%*, it really does make a difference. The lesson to learn here is: *Elasticsearch* doesn't do retention policies by default, so make sure you have something in place to discard old entries. Deleting them is as simple as sending an *HTTP DELETE* message to the index's endpoint:

```shell
$ curl -X DELETE http://elasticsearch:9200/fluentd-20180107 (TODO)
```

To find out what indexes it stores currently, and how much space those occupy, plus some other stats, you can use the `_stats` endpoint for example:

```shell
$ curl -s http://elasticsearch:9200/_stats (TODO) | jq --TODO select the names only?
```

*Elasticsearch* distributes their [own Docker images](TODO) officially, which are all based on CentOS. I wanted something smaller, so I went looking for an [Alpine Linux](TODO) based image, and found a pair of brilliant GitHub repos for [Elasticsearch](TODO) and [Kibana](TODO) too. My last problem was that they're not multi-arch, only support the *amd64* CPU architecture. The base `alpine` image is multi-arch though. Because of this, I could simply clone the repositories on one of the *ARM64* servers, build it and push it to my private registry. *Simple.* I don't have this process automated yet, though I'm not sure how often I'd want to rebuild these images anyway.

*Fluentd* is pretty cool, *being in CNCF and all*, and they also have an official Docker [library image](TODO). Docker supports logging directly into *Fluentd* out of the box. You need to give it some configuration in a config file, that will allow accepting log messages from Docker and then forwarding them into *Elasticsearch*. It looks something like this:

```
TODO fluentd.conf
```

You can do all sorts of *fancy* things with *Fluentd*, check out their [documentation](TODO) for all the input/output plugins and other processors (TODO term?) available. You can, for example, parse *Nginx* access log lines on-the-fly and extract fields from it:

```
TODO nginx parsing bit from fluentd.conf
```

I also build and store a Docker image for *Fluentd* in my private registry. They do have multi-arch images (TODO?), but you need to extend it to include the Docker logging module (TODO or something else?). It's pretty simple:

```Dockerfile
TODO fluentd Dockerfile
```

OK. We have covered all three parts of the logging stack, how do we run them? I use this configuration in my stack:

```yml
TODO EFK bit from the stack.yml
```

*Easy.* We defined three containers for our three applications, with *Elasticsearch* using a persistent volume for its data. The *Kibana* service also has some extra metadata to instruct the routing layer to put basic authentication in front of it. The *Fluentd* service exposes its port `22424 (TODO)` externally as well, which is needed because the Docker Engine will connect to it from the host, not from inside the Swarm stacks. Everything is ready now to start sending logs from the applications.

```yaml
TODO x-logging-settings
 nginx
 demo-site
 pygen (1 instance)
```

Since most of the logging configuration will be the same for all the applications, we can define the common bits in a [YAML anchor (TODO)](TODO), then we can import it into place, and override the `tag (TODO)` that is actually different for each application. This is really the only change to get the application logs written to the standard output and error streams forwarded into *Elasticsearch* through *Fluentd* instead of getting them written into files on the disk as JSON. For very chatty applications, and for the ones related to logging, we can choose to keep the logs in the default mode, but at least limit the amount of them being kept. You know, before you run out disk space.

```yaml
TODO json-file limit example
```

In *Kibana*, we just have to configure the index pattern once to hook it up. In our case, it will be `fluentd-*`, where the `*` will be date in `yyyyMMdd` format of when the log message was recorded. To then delete the old messages, you can do so by days as seen above.

The end result looks something like this:

> TODO image of the Kibana dashboard

## Monitoring

For monitoring, I chose a couple more *CNCF* projects (TODO are they part of it?). Metrics collection is done by the brilliant [Prometheus](TODO), which is a pull-based scraper. This means that the applications don't have to actively send their metrics to the server, but instead they only have to expose a simple HTTP endpoint with the metrics and their values listed in plain text format.

There are a growing number of applications supporting this method, one of them being the Docker Engine. With a tiny bit of configuration, you can get metrics out it about the number of running containers, image build stats, and much more. Besides these, you also get the standard *Go* stats about the application, like CPU and memory usage. Most client libraries for *Prometheus* support this out of the box, without any extra configuration.

While on the topic of libraries, make sure to check out the [official list](TODO) of supported languages and framework. You can probably find one for whatever programming language your application is written in. You can also find libraries for a bit higher level, that does not only give you language specific stats, but also framework specific one. For the [Flask](TODO) *HTTP server* library, I've written a simple one in *Python*. You only need to add in a single line of initialization by default, and you get your metrics endpoint with statistics about the *HTTP* requests handled by the application. Check it out on [GitHub](TODO), if you're interested.

There are also quite a few official exporter applications for common use-cases. The one I use if [node-exporter](TODO), that exposes metrics from the host, like CPU usage, memory and disk stats and much more. You could hook these up to *Prometheus'* [AlertManager (TODO name)](TODO) to notify you, when you're running out of disk space, or one of the boxes is spinning out of control.

For container-level metrics about *all* the running containers, I use [Telegraf](TODO). It gives you loads of details about them, again, CPU and memory metrics being the more important ones for me. The app itself is a bit more resource-hungry than I'd like it to be, but *that's life.*

For the final piece, visualization, I use the awesome [Grafana](TODO). It is another *CNCF project* (TODO?), has beautiful dashboards and it is super easy to set it up. It supports a few different kinds of backends, one of them is *Prometheus*, obviously. If you run it in the same stack with *Prometheus*, then the *datasource* configuration is as easy as entering `http://prometheus:9090` as the target URL, assuming the target service is called `prometheus`. You can easily set up authentication for it, but you can choose to keep parts of it public as well.

Let's get to the *YAML* config already? All right.

```yaml
TODO
 prometheus
 node-exporter
 telegraf
 grafana
```

*Easy-peasy.* (TODO spelling) The *Prometheus* configuration template I use with [docker-pygen](TODO) looks something like this:

```yaml
TODO prometheus config template
```

I mentioned my *Flask* exporter above, to get those recognised (and any others exposing metrics endpoints), I mark my services up with some labels, which will be picked up by the configuration above.

```yaml
TODO
 demo-site with prom config
 any other? - otherwise another Flask app as example
```

The `prometheus-x (TODO)` label tells about the fact that the service exposes a metrics endpoint, and the `prometheus-port (TODO)` label advertises the port it's accessible on. The former label is also used to set the service name for the given application. The really cool thing about the *Prometheus* [dns_sd_config (TODO name)](TODO) is that it automatically detects the *IP addresses* of all the running instances of the service, doesn't matter how many replicas it has. One goes down and comes back with a new *IP*? No problemo.

How you visualize the data you collect, is totally up to you. The end result could looks similar to this:

> TODO image of a Grafana dashboard

One thing to keep in mind though, *Prometheus* has a default retention policy of *15 days* (TODO), if you need more or less, don't forget to adjust it. For long-term storage, it's recommended you get *Prometheus* to forward it into something that is designed to do this, like [Influx DB (TODO space?)](TODO).

Before wrapping up the monitoring section, I need to mention another cool project I have running in my stack. [Portainer](TODO) is an awesome *Node.js* dashboard for Docker, that gives you all the information you need at a glance. You can view all the containers, images, services, stacks, configs, etc. your Docker instance is managing. Wait, *there's more*, you can also manage the Docker instance through it! For example, you can list out all the unused images and delete them. The same goes for volumes. You can filter the non-running containers too, and delete them at once. Having an awesome UI is really just the cherry on top.

> TODO image of Portainer

## What else?

Is there more I could monitor, you ask? *Oh, boy,* where do I start? There are so many more things I want to add to my cluster:

- [nginx metrics](TODO): For turning [Nginx](TODO) logs into metrics (though I might end up giving their new [Amplify](TODO) project a go)
- [blackbox-exporter](TODO): For collecting metrics from HTTP endpoints, including latency (TODO?), SSL expiry date and more
- [cloudflare-exporter](TODO): For exposing stats from [Cloudflare](TODO), the *CDN* provider I use
- [google-analytics-exporter](TODO) and [google-webmaster-tool-exporter](TODO): For gettings stats exposed for [Google Analytics](TODO) and [Webmasters tool](TODO)
- [github-exporter](TODO) and [dockerhub-exporter](TODO): For you know, stars and pulls and *stuff*
- An exporter for [GHost](TODO), if I find one - if not, I'll just have to write one myself

The list could go on and on. Monitoring is a pretty cool topic, and I haven't even touched on [OpenTracing](TODO), that can combine metrics of an event from multiple applications it affected. For example, you could get a nice trace of an *HTTP* request, all the systems it touched and the time it took for each of them to process. You can then easily visualize it with something, like [Zipkin](TODO) or [Jaeger](TODO).

I also really need to work on the alerting I have. Currently, I have [Uptime Robot](TODO) set up for externally monitoring my endpoints, and they send me a mail and a [Slack](TODO) message when they go down and come back up again. Check it out, they're pretty awesome! You can monitor 50 endpoints for free, and you can get a nice status page from them, [like mine](TODO), that you can also host on your own domain if you want to.

Make sure to check out the rest of the [series](https://blog.viktoradam.net/tag/home-lab/), if you're interested in seeing how I got to the point, where I need to have monitoring systems, and why is everything in Docker containers.

1. [Home Lab - Overview](https://blog.viktoradam.net/2018/01/03/home-lab-part1-overview/)
2. [Home Lab - Setting up for Docker](https://blog.viktoradam.net/2018/01/05/home-lab-part-2-docker-setup/)
3. [Home Lab - Swarming servers](https://blog.viktoradam.net/2018/01/13/home-lab-part3-swarm-cluster/)
4. *Home Lab - Configuring the cattle*
