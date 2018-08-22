# Moving home: To AWS with EC2, Lambda, API Gateway and Cloudflare for free

It was time for me to pack up my home stack and look for a free - even if temporary - cloud hosting for it until we go through an actual home move as well.

## Background

I was lucky enough get a job offered at a fantastic company I'm super excited about, and it's only about ten thousand miles (or 17k kilometers) from where we live. While we move halfway across the world, my self-hosted services and their servers need to either move or be offline. I have started looking for cloud providers with an easy to setup solution I could use for free until I'm ready to move things back to my own devices. I have finally settled for the [AWS free tier](https://aws.amazon.com/free/) services I was more-or-less familiar with already to some extent, and *Terraformed* my home lab into a data center only five thousand miles (or 8k kilometers) away from where it used to run.

This post is about changing infrastructure configuration from YAML files to [HCL](https://www.terraform.io/docs/configuration/syntax.html), and rolling these changes out with zero downtime, though also sacrificing some of the services in the process.

## Getting familiar with AWS

First, I looked at the offerings of the big, main cloud providers to see where could I host a couple of services running in Docker. Each of them had pretty decent and cheap options for running a single virtual machine instance, but I thought I'll have a look at the obvious choice, AWS and its free tier. It comes with a lot of services with basic options free for the first 12 months, and since I had a little bit of experience with it, I gave it a go.

The first thing I wanted to try was running a `t2.micro` [EC2 instance](https://aws.amazon.com/ec2/) and install Docker on it, to see if that works as easily as it should be, and it did. I chose Ubuntu as the [AMI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html), fired it up and tested the SSH connection. On the VM itself, I just installed Docker with a simple one-liner.

```shell
$ curl -fsSL get.docker.com | sh
```

Did a quick `docker version` afterwards, and I saw that it's all good so far. In the meantime, I was working on the target stack locally, with a [Traefik](https://traefik.io/) reverse proxy for routing and automatic [Let's Encrypt](https://letsencrypt.org/) certificate management, this [Ghost](https://ghost.org/) blog, and an [Nginx](https://www.nginx.com/) instance for redirecting the domains I won't maintain while I move. Then I started to think that this is a bit crazy, and I could do something more *AWS-native* for this last part.

I already had some [Lambda](https://aws.amazon.com/lambda/) and [API Gateway](https://aws.amazon.com/api-gateway/) experience from work, and I thought this would make much more sense to send simple redirects. And when I say simple, this is what my Lambda handler looks like.

```javascript
exports.handler = async (event, context, callback) => {
    callback(null, {
        statusCode: 302,
        headers: {
            "Location": "https://blog.viktoradam.net"
        },
        body: null
    });
}
```

I've created the Lambda function on the [AWS Console](https://console.aws.amazon.com/console/home), and configured an integration for it with API Gateway. This takes care of most of the appropriate configuration that connects incoming HTTP requests to the handler function, attaches the necessary [policies](https://docs.aws.amazon.com/apigateway/latest/developerguide/integrating-api-with-aws-services-lambda.html#api-as-lambda-proxy-setup-iam-role-policies) and integrations with logs and metrics, etc. After this, I wanted to route all requests from my `www.viktoradam.net` domain to this integration, which needed configuring a [custom domain](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html) for API Gateway. That in turn needs a certificate, so I went to [Cloudflare](https://www.cloudflare.com/), my CDN provider, and generated a new [origin certificate](https://support.cloudflare.com/hc/en-us/articles/115000479507-Creating-and-managing-certificates-with-Origin-CA). I saved the certificate and key files, plus grabbed the Cloudflare [origin CA root](https://support.cloudflare.com/hc/en-us/articles/218689638-What-are-the-root-certificate-authorities-CAs-used-with-CloudFlare-Origin-CA-), and uploaded the certificate into [ACM](https://aws.amazon.com/certificate-manager/). Now I was able to set up the custom domain mapping, using the domain name and the uploaded certificate. I wanted this domain to handle all requests to any path with the Lambda function I created previously, so I set the [base path mapping](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html) to use the API created earlier with its `default` stage for all requests - just leave the `Path` empty for this.

The endpoint was now almost ready, AWS estimated it takes about 40 minutes to roll it out globally. I started testing the [CloudFront](https://aws.amazon.com/cloudfront/) domain that was generated for this setup with a simple [cURL](https://curl.haxx.se/) request.

```shell
$ curl -s -v -H 'Host: www.viktoradam.net' https://d1234abcd.cloudfront.net/ > /dev/null
```

Once it started working, I was ready to change the DNS record in Cloudflare. While self-hosting this endpoint, it had an `A` record, with the IP address pointing to my origin server. With this CloudFront setup, you'll need a `CNAME` record, where the value is the domain name AWS gives you in the `Domain name` field of the API custom domain. (TODO maybe insert a picture) After a few seconds, the domain was now pointing to AWS, and after a quick Cloudflare cache purge, it was ready for testing.

```shell
$ curl -s -v https://www.viktoradam.net/ > /dev/null
```

I then went on to hook up two more subdomains to this integration before I realized that manually setting the whole thing up is not the way to go. I need something repeatable and codified, so it's easy to redo if I mess something up, or forget how I did a particular bit of configuration before.

## Configuration as code

When I think about declarative AWS infrastructure configuration, [Terraform](https://www.terraform.io/) and [CloudFormation](https://aws.amazon.com/cloudformation/) comes to my mind immediately. I haven't tried CloudFormation (spelling) yet, but I did have some experience with Terraform for similar setup, so I went with that one. Quickly rebuilt the [VS code](https://code.visualstudio.com/) image I use for developing this stack, based on [jess/vscode](https://github.com/jessfraz/dockerfiles/blob/master/vscode/Dockerfile), and added the Terraform binary in there. I have added the basic configuration then to be able to initialize the workspace.

```python
variable "region" {}
variable "account_id" {}

terraform {
  backend "local" {
    path = "state/terraform.tfstate"
  }
}

provider "aws" {
  region = "${var.region}"
}
```

Now I was ready to run `terraform init` that downloads the plugins for the providers it can find in the `.tf` files, in my case, for AWS. Next, I prepared the JavaScript file for the Lambda function body in a subfolder, and wrote a simple Shell script to `zip` it, Terraform will want to upload it in this format. Once I had the `.zip` file, I prepared the *HCL* for the function with a different name, so it wouldn't clash with the manually created one.

```python
data "aws_iam_role" "lambda_basic_execution" {
  name = "lambda_basic_execution"
}

resource "aws_lambda_function" "lambda_blog_redirect" {
  function_name    = "BlogRedirect"
  filename         = "lambda/blog_redirects.zip"
  source_code_hash = "${base64sha256(file("lambda/blog_redirects.zip"))}"
  handler          = "blog_redirects.handler"
  runtime          = "nodejs8.10"
  role             = "${data.aws_iam_role.lambda_basic_execution.arn}"
}
```

OK, I gave it a go with `terraform plan`, to see what it would do, then quickly realized that I haven't given any AWS API keys to it yet, so it couldn't really do anything. The [AWS provider](https://www.terraform.io/docs/providers/aws/) can take its credentials from a few different places, one of them being a configuration file like the one below, and Terraform looks for it by default at the `~/.aws/credentials` path.

```ini
[default]
aws_access_key_id = abcABC123
aws_secret_access_key = xyzXYZ456
```

I just had to quickly create a new user for [programmatic access](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html) in [IAM](https://aws.amazon.com/iam/), then saved the access and secret keys in the file above. Now `terraform plan` looked much happier. With [plan](https://www.terraform.io/docs/commands/plan.html), it prints the changes it would need to do, compared to the [state](https://www.terraform.io/docs/state/) it already manages - which was empty for me at this point. To actually execute the plan and create the resources, use `terraform apply`. The [apply](https://www.terraform.io/docs/commands/apply.html) sub-command will provision the changes, and save the results in a state file, which will then be used on subsequent runs to compute the difference Terraform should resolve.

Lambda was easy to set up, API Gateway is much more cumbersome unfortunately. I tried to follow the [Serverless guide](https://www.terraform.io/docs/providers/aws/guides/serverless-with-aws-lambda-and-api-gateway.html) on the Terraform documentation site, but it didn't actually work. Some [GitHub issues](https://github.com/hashicorp/terraform/issues/10157#issuecomment-410132880) suggest it needs some updating now, but I could finally get it working with some configuration like this below.

```python
# The API to configure
resource "aws_api_gateway_rest_api" "apigw_rest_blog" {
  name        = "BlogRedirect"
  description = "Redirects all request to the blog"
}

# The API resource for handling all requests
resource "aws_api_gateway_resource" "apigw_blog_resource" {
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  parent_id   = "${aws_api_gateway_rest_api.apigw_rest_blog.root_resource_id}"
  path_part   = "{proxy+}"
}

# The HTTP method config below for /* request paths
resource "aws_api_gateway_method" "apigw_blog_method_GET" {
  rest_api_id   = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id   = "${aws_api_gateway_resource.apigw_blog_resource.id}"
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "apigw_blog_method_200" {
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id = "${aws_api_gateway_resource.apigw_blog_resource.id}"
  http_method = "${aws_api_gateway_method.apigw_blog_method_GET.http_method}"
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "apigw_blog_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id = "${aws_api_gateway_method.apigw_blog_method_GET.resource_id}"
  http_method = "${aws_api_gateway_method.apigw_blog_method_GET.http_method}"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "${aws_lambda_function.lambda_blog_redirect.invoke_arn}"
}

resource "aws_api_gateway_integration_response" "apigw_blog_integration_response" 
{
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id = "${aws_api_gateway_resource.apigw_blog_resource.id}"
  http_method = "${aws_api_gateway_method.apigw_blog_method_GET.http_method}"
  status_code = "${aws_api_gateway_method_response.apigw_blog_method_200.status_co
de}"

  response_templates = {
    "application/json" = ""
  }
}

# The HTTP method config below for / (root) request paths
resource "aws_api_gateway_method" "apigw_blog_method_root_GET" {
  rest_api_id   = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id   = "${aws_api_gateway_rest_api.apigw_rest_blog.root_resource_id}"
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "apigw_blog_method_root_200" {
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id = "${aws_api_gateway_rest_api.apigw_rest_blog.root_resource_id}"
  http_method = "${aws_api_gateway_method.apigw_blog_method_root_GET.http_method}"
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "apigw_blog_root_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id = "${aws_api_gateway_method.apigw_blog_method_root_GET.resource_id}"
  http_method = "${aws_api_gateway_method.apigw_blog_method_root_GET.http_method}"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "${aws_lambda_function.lambda_blog_redirect.invoke_arn}"
}

resource "aws_api_gateway_integration_response" "apigw_blog_root_integration_response" {
  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  resource_id = "${aws_api_gateway_method.apigw_blog_method_root_GET.resource_id}"
  http_method = "${aws_api_gateway_method.apigw_blog_method_root_GET.http_method}"
  status_code = "${aws_api_gateway_method_response.apigw_blog_method_root_200.status_code}"

  response_templates = {
    "application/json" = ""
  }
}

# The deployment configuration of the API
resource "aws_api_gateway_deployment" "apigw_blog_deployment" {
  depends_on = [
    "aws_api_gateway_integration.apigw_blog_integration",
    "aws_api_gateway_integration.apigw_blog_root_integration",
  ]

  rest_api_id = "${aws_api_gateway_rest_api.apigw_rest_blog.id}"
  stage_name  = "live"
}

# Finally the permission to invoke Lambda functions
resource "aws_lambda_permission" "apigw_blog_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.lambda_blog_redirect.arn}"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_deployment.apigw_blog_deployment.execution_arn}/*/*"
}
```

This has set up everything, up to the CloudFront URL I could trigger the execution, you can try this with a simple cURL command. To make things easier, you can configure this URL as an output in Terraform, so that after successful runs, it prints its value to the console.

```python
output "blog_redir_base_url" {
  value = "${aws_api_gateway_deployment.apigw_blog_deployment.invoke_url}"
}
```

The only bit missing now was the custom domain mapping, and hooking it all up to Cloudflare.

## Switching DNS

> TODO Terraform import Cloudflare, connecting resources, wait until the CloudFront domain is available

## Moving Ghost

> TODO Docker setup, Traefik with ACME, Git sync, SSH/SCP script, Docker volume setup, test with cURL, Terraform import EC2 data, rollout with DNS change

## Conclusion

> TODO monitoring services

