# Moving home: To AWS with EC2, Lambda, API Gateway and Cloudflare for free

It was time for me to pack up my home stack and look for a free - even if temporary - cloud hosting for it until we go through an actual home move as well.

## Background

I was lucky enough get a job offered at a fantastic company I'm super excited about, and it's only about ten thousand miles (or 17k kilometres) from where we live. While we move halfway across the world, my self-hosted services and their servers need to either move or be offline. I have started looking for cloud providers with an easy to setup solution I could use for free until I'm ready to move things back to my own devices. I have finally settled for the [AWS free tier](TODO) services I was more-or-less familiar with already to some extent, and *Terraformed* my home lab into a datacenter only five thousand miles (or 8k kilometres) away from where it used to run.

This post is about changing infrastructure configuration from YAML files to [HCL](TODO), and rolling these changes out with zero downtime, though also sacrificing some of the services in the process.

## Getting familiar with AWS

First, I looked at the offerings of the big, main cloud providers to see where could I host a couple of services running in Docker. Each of them had pretty decent and cheap options for running a single virtual machine instance, but I thought I'll have a look at the obvious choice, AWS and its free tier. It comes with a lot of services with basic options free for the first 12 months, and since I had a little bit of experience with it, I gave it a go.

The first thing I wanted to try was running a `t2.micro` (TODO) [EC2 instance](TODO) and install Docker on it, to see if that works as easily as it should be, and it did. I chose Ubuntu as the [AMI](TODO), fired it up and tested the SSH connection. On the VM itself, I just installed Docker with a simple one-liner.

```shell
$ curl -fsSL get.docker.com | sh (TODO sudo?)
```

Did a quick `docker version` afterwards, and I saw that it's all good so far. In the meantime, I was working on the target stack locally, with a [Traefik](TODO) reverse proxy for routing and automatic [Let's Encrypt](TODO) certificate management, this [Ghost](TODO) blog, and an [Nginx](TODO) instance for redirecting the domains I won't maintain while I move. Then I started to think that this is a bit crazy, and I could do something more *AWS-native* for this last part.

I already had some [Lambda](TODO) and [API Gateway](TODO) experience from work, and I thought this would make much more sense to send simple redirects. And when I say simple, this is what my Lambda handler looks like.

```javascript
TODO lambda function body
```

I've created the Lambda function on the [AWS Console], and configured an integration for it with API Gateway. This takes care of most of the appropriate configuration that connects incoming HTTP requests to the handler function, attaches the necessary [policies](TODO) and integrations with logs and metrics, etc. After this, I wanted to route all requests from my `www.viktoradam.net` domain to this integration, which needed configuring a [custom domain](TODO) for API Gateway. That in turn needs a certificate, so I went to [Cloudflare](TODO), my CDN provider, and generated a new [origin certificate](TODO). I saved the certificate and key files (TODO), plus grabbed the Cloudflare [origin root CA](TODO name? + link), and uploaded the certificate into [ACM](TODO). Now I was able to set up the custom domain mapping, using the domain name and the uploaded certificate. I wanted this domain to handle all requests to any path with the Lambda function I created previously, so I set the [base path mapping](TODO) to use the API created earlier with its `default` stage for all requests - just leave the `Path` empty for this.

The endpoint was now almost ready, AWS estimated it takes about 40 minutes to roll it out globally. I started testing the [CloudFront](TODO) domain that was generated for this setup with a simple [cURL](TODO) request.

```shell
$ curl -s -v -H 'Host: www.viktoradam.net' https://d1234abcd.cloudfront.net/ > /dev/null (TODO does it need the stage?)
```

Once it started working, I was ready to change the DNS record in Cloudflare. While self-hosting this endpoint, it had an `A` record, with the IP address pointing to my origin server. With this CloudFront setup, you'll need a `CNAME` record, where the value is the domain name AWS gives you in the `Domain name` field of the API custom domain. (TODO maybe insert a picture) After a few seconds, the domain was now pointing to AWS, and after a quick Cloudflare cache purge, it was ready for testing.

```shell
$ curl -s -v https://www.viktoradam.net/ > /dev/null
```

I then went on to hook up two more subdomains to this integration before I realised that manually setting the whole thing up is not the way to go. I need something repeatable and codified, so it's easy to redo if I mess something up, or forget how I did a particular bit of configuration before.

## Configuration as code

When I think about declarative AWS infrastructure configuration, [Terraform](TODO) and [CloudFormation](TODO) comes to my mind immediately. I haven't tried CloudFormation (spelling) yet, but I did have some experience with Terraform for similar setup, so I went with that one. Quickly rebuilt the [VS code](TODO) image I use for developing this stack, based on [jess/vscode](TODO), and added the Terraform binary in there. I have added the basic configuration then to be able to initialize the workspace.

```hcl
(TODO can HCL be syntax-colored?)
base config
variables
```

Now I was ready to run `terraform init` that downloads the plugins for the providers it can find in the `.tf` files, in my case, for AWS. Next, I prepared the JavaScript file for the Lambda function body in a subfolder, and wrote a simple Shell script to `zip` it, Terraform will want to upload it in this format. Once I had the `.zip` file, I prepared the *HCL* for the function with a different name, so it wouldn't clash with the manually created one.

```hcl
(TODO HCL?)
resource lambda ...
```

OK, I gave it a go with `terraform plan`, to see what it would do, then quickly realised that I haven't given any AWS API keys to it yet, so it couldn't really do anything. The [AWS provider](TODO) can take its credentials from a [few different places](TODO), one of them being a configuration file like the one below, and Terraform looks for it by default at the `~/.aws/credentials/TODO` path.

```toml/ini
Type?
access=
secret=
```

I just had to quickly create a new user for [programmatic access](TODO) in [IAM](TODO), then saved the access and secret keys in the file above. Now `terraform plan` looked much happier. With [plan](TODO), it prints the changes it would need to do, compared to the [state](TODO) it already manages - which was empty for me at this point. To actually execute the plan and create the resources, use `terraform apply`. The [apply](TODO) sub-command will provision the changes, and save the results in a state file, which will then be used on subsequent runs to compute the difference Terraform should resolve.

Lambda was easy to set up, API Gateway is much more cumbersome unfortunately. I tried to follow the [Serverless example](TODO) on the Terraform documentation site, but it didn't actually work. Some [GitHub issues](TODO) suggest it needs some updating now, but I could finally get it working with some configuration like this below.

```hcl
(TODO hcl?)
resource api_...
```

This has set up everything, up to the CloudFront URL I could trigger the execution, you can try this with a simple cURL command. To make things easier, you can configure this URL as an output in Terraform, so that after successful runs, it prints its value to the console.

```hcl
(TODO hcl?)
output ...
```

The only bit missing now was the custom domain mapping, and hooking it all up to Cloudflare.

## Switching DNS

> TODO Terraform import Cloudflare, connecting resources, wait until the CloudFront domain is available

## Moving Ghost

> TODO Docker setup, Traefik with ACME, Git sync, SSH/SCP script, Docker volume setup, test with cURL, Terraform import EC2 data, rollout with DNS change

## Conclusion

> TODO

