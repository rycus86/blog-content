# Automatic domain and SSL management

Creating and maintaining DNS records on Cloudflare, with secure communication to the origin servers using certificates from Let's Encrypt, and how we to make it painless and fully automated.

*Automate, automate, automate!* I had a fairly frictionless process for spinning up applications on new domain names with automatic SSL certificate management. Still, there were a few manual steps at the initial setup, plus not a lot of visibility on their state and progress. Well, no more!

## Starting point

In a [previous post](https://blog.viktoradam.net/2018/01/20/home-lab-part4-auto-configuration/), I mentioned I use [Cloudflare](https://www.cloudflare.com/) for content delivery and DNS management. My dynamic IP address I get from my ISP was kept up-to-date using a container with my [ddclient image](https://hub.docker.com/r/rycus86/ddclient/). Origin certificates are all coming from [Let's Encrypt](https://letsencrypt.org/) using their [certbot](https://certbot.eff.org/) client. The HTTPS traffic is then handled by an [Nginx](https://www.nginx.com/) instance, using these certificates. The initial setup process looks like this for new subdomains:

1. Register the new subdomain on *Cloudflare*'s dashboard __manually__ *(sigh...)*
2. Get the new Docker services running through the automated pipeline
3. *ddclient* and the *certbot* helper picks up the new subdomain
4. The *Nginx* configuration file is updated for the new endpoint, including configuration for the SSL certificate  
  *Note:* the certificate does not exist at this point, so the initial configuration reload __fails__ *(eh...)*
5. *certbot* fetches the new certificate and saves it on a shared volume, so *Nginx* can access it
6. With no events generated at this point, I have to log in to the Swarm manager node and __manually__ send a `HUP` signal to the *Nginx* container *(sigh...)*
7. *And now we're in business..*
8. Further updates are fully automated, with *ddclient* keeping the IP address up-to-date on the DNS record, and *certbot* renewing the certificates when it's time

One could argue, it's not *too* bad, having to do only the DNS registration manually, plus a quick `docker kill` on an *SSH* session. It does mean though that I have to actively participate in and supervise the launch of services on a new subdomain.

So, how do I get to spin up new endpoints with a `git push` __only__, sitting on a train, using a *spotty* (TODO?) mobile data connection, in a __fully__ automated way? *With a Python app, of corse... (TODO spelling)*

## The present future

All of the 3rd party services and tools I mentioned above have awesome APIs and/or great support for automation. I needed a consistent workflow involving all of them, executing steps in the right order, and notifying related services as and when needed. Half of the problem with the original process is timing issues, this is what I needed to resolve.

The new workflow is this:

1. Launch the new service with a `git push` and appropriate labels in the stack *YAML* file
2. The *Nginx* configuration is updated, the container is signalled, but it fails to reload because of the missing certficate, so it'll continue running with the previous configuration
3. The [domain automation service](https://github.com/rycus86/domain-automation) is signalled to kick-off an out-of-schedule update - TODO or by a Docker service event?
4. It collects all the subdomains from the running Docker services' labels, and processes them one by one
5. It grabs the current public IP address from [api.ipify.org](TODO website)
6. Creates or updates the related DNS record in Cloudflare, using their Python [API client](TODO)
7. Runs *certbot* through [subprocess](TODO Python docs link)
8. Sends a signal to containers with appropriate labels (e.g. to *Nginx* to reload), in case a certificate was renewed or it was fetched for the first time
9. Sends a message on Slack for errors, DNS record updates and certificate changes
10. Also logs into my [Elasticsearch-Fluentd-Kibana](https://blog.viktoradam.net/2018/02/06/home-lab-part5-monitoring-madness/) stack

This workflow is then repeated on a schedule, so that public IP address changes and certificate renewal happen if they need to. To reiterate, the __only__ manual step in this process is now the `git push` with the code or configuration changes, like it *should be*. *Yay!*

On a related note, *certbot* is actually implemented in Python, but its main purpose is to process requests taken from command line arguments, and that means it is [very](TODO links), [very](TODO) difficult to use it as a library. I'm not *particularly* happy about executing it as an external process, but it is still better than running it on a separate schedule.

## Components

It was *surprisingly* easy to get this working, thanks to the awesome open-source libraries available for the 3rd party services and tools. The Docker side of automation is handled by the awesome [docker-py](TODO) library, of corse (TODO).

The *ipify* (TODO name) service is used to get the public IP address for the DNS update. It serves XX (TODO how many?) requests daily, and it provides responses in [JSON](TODO), [JSONP](TODO) and [plain text](TODO) format as well (TODO any more?). It is free, [open-source](TODO GitHub) link, and just plain *awesome*! I'm using it in plain text mode, with the [requests](TODO) Python library, like this:

```python
ip_address = requests.get('https://api.ipify.org').text  # TODO
```

*Cloudflare* has a *wonderful* [API](https://api.cloudflare.com/), accompanied (TODO?) with a [Python SDK](https://github.com/cloudflare/python-cloudflare). This makes things super easy:

```python
TODO Cf example for get zone, get dns records, update one
```

The snippet above would fetch the *zone* details for `example.com`, list the DNS records, take the first *A* or *AAAA* record, and update it with the IP address `8.8.8.8`. See? *Super easy!*

[certbot](TODO) is also open-source, as-is the underlying [acme](TODO) library that handles talking to the *Let's Encrypt* API (TODO what is the host?). *certbot*'s architecture is modular and it supports plugins. I used to use the default [HTTP-01](TODO link) challenge, where the tool gave me a token that I had to serve up on HTTP on the domain I was verifying. This was done using *Nginx* and shared volume for saving the challenge content, and it was working OK. I found another way that is *much* better for me though. The [DNS-01](TODO link) challenge needs you to have a *TXT* DNS record set up with the challenge content on your domain, so that *Let's Encrypt* can verify your domain by checking it. This is very easy to do on *Cloudflare* using their APIs. Would I code it up? *Absolutely.* Do I have to? *Nope.* The [cloudflare-certbot-plugin-TODO-name](TODO) is doing exactly this. All I need to do is to make sure the plugin is available:

```shell
$ pip install cf-certbot-plugin (TODO)
```

With this, I can now pass settings to *certbot* to do the challenge and verification through *Cloudflare*:

```shell
$ certbot --blabla (TODO) --propagation 15
```

Most of the parameters are pretty self-explanatory. We ask for the specific *DNS-01* challenge, agree to the terms of service and pass our email address. The `--dns-propagation-seconds-TODO 15` flag allows 15 seconds for DNS propagation after the new *TXT* record is in place, and *certbot* only starts the verification after this. On completion, either by failing or succeeding (TODO?), the DNS record is removed by plugin automatically. *Nice one!*

The [Slack](TODO) notification is done through their *excellent* [API](TODO docs). Again, I didn't have to write the API communication layer myself, the [slack-py TODO](TODO) library takes care of it for me. Sending a message is as easy as:

```python
client = SlackClient(..) TODO
client.login() ?
client.postMessage(..)
```

You only need to log in once, then you can post as many messages as you wish, [within reason](TODO limits).

Signalling the containers I need is a *bit* tricky. The *domain automation* app has to run on a Swarm manager node, so that it has access to the Docker API, including the service related endpoints. You can't signal services or their tasks directly, only individual containers, which might not run on the same node where the app is running. To get around the problem, I'm launching a new *global* service with the same image that the app uses, and I specify a different launch command that will only execute the local signal send, not the main application ([see the code here](TODO)). The service is set to never restart, so each of its tasks only runs once, then stops. The command line equivalent of this would be something like this:

```shell
$ docker service create --mode global ... TODO
```

In the Python component, the final task states are collected along with the standard output and error messages, if available. I'm using the *awesome* [Fluentd](TODO) logging driver, so the messages will be available in [Kibana](TODO), in case I have to check what happened.

The application logs themselves are also going into [Elasticsearch](TODO) through *Fluentd*. This is easily done by changing the `log_driver` in the stack's [Composefile](TODO reference):

```yaml
TODO log config
```

I mentioned above that the trigger and configuration for the Docker bits live in service and container labels in the stack *YAML*. For example, if I'd have an `nginx` service to signal and two other services to manage the subdomains for, it would look something like this:

```yaml
version: '3.5'
services:
  
  nginx:
    TODO
  
  sample:
    TODO
  
  demo:
    TODO
```

Finally, if you're more of a *visual type* of person, this is how the workflow looks like again, drawn using the *brilliant* [PlantUML](TODO).

> TODO PlantUML sequence diagram

# Wrap up

I am now testing this tool in my [Home Lab](TODO tag link), and if all works out, it will replace the *ddclient*, *certbot* and their related services with all the tasks that come with them - a total of *10 containers*. It is a nice save of resources, too!

I have also started open-sourcing all my Docker stack configuration, starting with the [DNS/SSL management stack](TODO github). Eventually, I want to have them all on [GitHub](TODO), so its easier to demonstrate and write about them. If you're checking, don't worry about the `.conf` files, the contents are encrypted using [git-crypt](TODO), which is an *awesome* tool, doing automatic, transparent (TODO?) encryption and decryption of files that match the patterns defined in the `.gitattributes (TODO?)` file. *You know, for sensitive stuff.*

Hope you enjoyed this post, and it got you inspired to start building the automation around your own stack. I'm *absolutely* happy for you to use my app and its [Docker image](TODO), and I'm also willing to accept pull-requests on the [GitHub](TODO) repo, if all you're missing is another DNS or SSL management module.

If you're going down these routes and want to get in touch, find me on Twitter [@rycus86](TODO)!

*Happy hacking!*

