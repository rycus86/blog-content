# Swarm secrets made easy

A recent Docker update came with a small but important change for service secrets and configs, that enables a much easier way to manage and update them when deploying Swarm stacks.

*TL;DR* This post describes an automated way to create and update secrets or configs, when they are managed through a Composefile, and are deployed as a stack, along with the services using them. To avoid repeating *"secrets and configs"* all over the post, I'm going to talk about secrets, but the same thing applies to configs as well.

## Updating secrets the hard way

Docker Swarm [secrets](TODO) (and [configs](TODO)) are immutable, which means, once created, their content cannot be changed. If you want to update the data they hold, you need to create them under a new name, and update the services using them to forget about the old secret, and reference the new one instead. Let's look at an example of how we could do it from the command line, without stacks first.

```shell
$ cat nginx.conf | docker secret create nginx-config-v1 -
ffrkdpnaw7jkrxmhyjfr4a275
$ docker secret ls
ID                          NAME                CREATED             UPDATED
ffrkdpnaw7jkrxmhyjfr4a275   nginx-config-v1     5 seconds ago       5 seconds ago
```

Our first secret is now created and is ready to use with services. Let's start one.

```shell
$ docker service create --detach=true --name server --secret source=nginx-config-v1,target=/etc/nginx/conf.d/default.conf,mode=0400 nginx:1.13.7
wlk2axginrhjb7vtkhovk2e12
$ docker service ls
ID                  NAME                MODE                REPLICAS            IMAGE               PORTS
wlk2axginrhj        server              replicated          1/1                 nginx:1.13.7
$ docker service inspect server
[
    {
        "ID": "wlk2axginrhjb7vtkhovk2e12",
        "Version": {
            "Index": 84
        },
        "CreatedAt": "2018-02-26T07:17:43.36393357Z",
        "UpdatedAt": "2018-02-26T07:17:43.36393357Z",
        "Spec": {
            "Name": "server",
            "Labels": {},
            "TaskTemplate": {
                "ContainerSpec": {
                    "Image": "nginx:1.13.7",
                    "StopGracePeriod": 10000000000,
                    "DNSConfig": {},
                    "Secrets": [
                        {
                            "File": {
                                "Name": "/etc/nginx/conf.d/default.conf",
                                "UID": "0",
                                "GID": "0",
                                "Mode": 256
                            },
                            "SecretID": "ffrkdpnaw7jkrxmhyjfr4a275",
                            "SecretName": "nginx-config-v1"
                        }
                    ]
                },
                ...
```

You can see it from the `docker inspect` output, that the secret was successfully declared to be loaded at `/etc/nginx/conf.d/default.conf` inside the container. The mode `256` might look a little strange, that's actually `o400` in decimal, but let's double-check:

```shell
$ docker exec -it server.1.zog0eqk9oluux9q68ez54f2kx ls -l /etc/nginx/conf.d/default.conf
-r-------- 1 root root 21 Feb 26 07:33 /etc/nginx/conf.d/default.conf
```

*All good there!* OK, so let's update our configuration file now! As stated above, our only option is to create a new secret, and update the service with its reference.

```shell
$ cat nginx.conf | docker secret create nginx-config-v2 -
wnddsd2lm6kojlgcprhm1jkem
$ docker secret ls
ID                          NAME                CREATED             UPDATED
ffrkdpnaw7jkrxmhyjfr4a275   nginx-config-v1     24 minutes ago      24 minutes ago
wnddsd2lm6kojlgcprhm1jkem   nginx-config-v2     6 seconds ago       6 seconds ago
$ docker service update server --secret-rm nginx-config-v1 --secret-add source=nginx-config-v2,target=/etc/nginx/conf.d/default.conf,mode=0400 --update-order start-first --detach=true
server
$ docker service ps server
ID                  NAME                IMAGE               NODE                DESIRED STATE       CURRENT STATE            ERROR               PORTS
iyu33g3zibr3        server.1            nginx:1.13.7        moby                Running             Running 14 seconds ago
zog0eqk9oluu         \_ server.1        nginx:1.13.7        moby                Shutdown            Shutdown 11 seconds ago
$ docker service inspect server
[
    {
        "ID": "a9o72ncgj09ndph64my1dtkxf",
        "Version": {
            "Index": 1584
        },
        "CreatedAt": "2018-02-26T07:33:53.376179313Z",
        "UpdatedAt": "2018-02-26T07:40:28.712701204Z",
        "Spec": {
            "Name": "server",
            "Labels": {},
            "TaskTemplate": {
                "ContainerSpec": {
                    "Image": "nginx:1.13.7",
                    "Args": [
                        "sh"
                    ],
                    "TTY": true,
                    "StopGracePeriod": 10000000000,
                    "DNSConfig": {},
                    "Secrets": [
                        {
                            "File": {
                                "Name": "/etc/nginx/conf.d/default.conf",
                                "UID": "0",
                                "GID": "0",
                                "Mode": 256
                            },
                            "SecretID": "wnddsd2lm6kojlgcprhm1jkem",
                            "SecretName": "nginx-config-v2"
                        }
                    ]
                },
                ...
        "PreviousSpec": {
            "Name": "server",
            "Labels": {},
            "TaskTemplate": {
                "ContainerSpec": {
                    "Image": "nginx:1.13.7",
                    "Args": [
                        "sh"
                    ],
                    "TTY": true,
                    "DNSConfig": {},
                    "Secrets": [
                        {
                            "File": {
                                "Name": "/etc/nginx/conf.d/default.conf",
                                "UID": "0",
                                "GID": "0",
                                "Mode": 256
                            },
                            "SecretID": "ffrkdpnaw7jkrxmhyjfr4a275",
                            "SecretName": "nginx-config-v1"
                        }
                    ]
                },
                ...
```

We can see now, that the new service `Spec` refers to the `nginx-config-v2` secret. In case the update fails, Swarm could roll back to the previous version of the service definition, described in the `PreviousSpec` section, which still refers to the previous `nginx-config-v1` secret. This is one of the main reasons for immutable secrets.

> If we would update the secret itself, we would lose the previous content to rollback to.

Before moving on to the next section, let's clean up after ourselves.

```shell
$ docker service rm server
server
$ docker secret rm nginx-config-v1 nginx-config-v2
nginx-config-v1
nginx-config-v2
```

## Secrets in stacks

Let's look at a *less interactive* example for declaring our secret and the service that uses it. The sample above would roughly translate to this Composefile:

```yaml
version: '3.4'
services:

  server:
    image: nginx:1.13.7
    secrets:
      - source: nginx-config
        target: /etc/nginx/conf.d/default.conf
        mode: 0400

secrets:
  nginx-config:
    file: ./nginx.conf
```

To start the service, we're going to deploy this as a Swarm stack.

```shell
$ ls
nginx.conf    stack.yml
$ docker stack deploy -c stack.yml sample
Creating network sample_default
Creating service sample_server
$ docker secret ls
ID                          NAME                  CREATED              UPDATED
t6nxubtysp8912tu6wql96tbr   sample_nginx-config   About a minute ago   About a minute ago
$ docker service ls
ID                  NAME                MODE                REPLICAS            IMAGE               PORTS
a4iyi0j4nr39        sample_server       replicated          1/1                 nginx:1.13.7
$ docker service inspect sample_server
[
    {
        "ID": "a4iyi0j4nr399x51mea9qrzdv",
        "Version": {
            "Index": 1592
        },
        "CreatedAt": "2018-02-26T07:51:41.65482285Z",
        "UpdatedAt": "2018-02-26T07:51:41.656180056Z",
        "Spec": {
            "Name": "sample_server",
            "Labels": {
                "com.docker.stack.image": "nginx:1.13.7",
                "com.docker.stack.namespace": "sample"
            },
            "TaskTemplate": {
                "ContainerSpec": {
                    "Image": "nginx:1.13.7",
                    "Labels": {
                        "com.docker.stack.namespace": "sample"
                    },
                    "Privileges": {
                        "CredentialSpec": null,
                        "SELinuxContext": null
                    },
                    "StopGracePeriod": 10000000000,
                    "DNSConfig": {},
                    "Secrets": [
                        {
                            "File": {
                                "Name": "/etc/nginx/conf.d/default.conf",
                                "UID": "0",
                                "GID": "0",
                                "Mode": 256
                            },
                            "SecretID": "t6nxubtysp8912tu6wql96tbr",
                            "SecretName": "sample_nginx-config"
                        }
                    ]
                },
                ...
```

This looks very similar to what we've seen before, our secret just got prefixed with the stack *namespace*, and has become `sample_nginx-config`. OK, *great*, but how can we update our configuration file now?

```shell
$ echo '# changed' >> nginx.conf
$ docker stack deploy -c stack.yml sample
failed to update secret sample_nginx-config: Error response from daemon: rpc error: code = InvalidArgument desc = only updates to Labels are allowed
```

So, *that* didn't work. We'll need to update the secret name.

```yaml
version: '3.4'
services:

  server:
    image: nginx:1.13.7
    secrets:
      - source: nginx-config-v2
        target: /etc/nginx/conf.d/default.conf
        mode: 0400

secrets:
  nginx-config-v2:
    file: ./nginx.conf
```

Well, we didn't gain much, compared two the initial example above. We now have to update the secret's name in two places. At least, you can deploy the changes now.

```shell
$ docker stack deploy -c stack.yml sample
Updating service sample_server (id: a4iyi0j4nr399x51mea9qrzdv)
$ docker service inspect sample_server
[
    {
        "ID": "a4iyi0j4nr399x51mea9qrzdv",
        "Version": {
            "Index": 24057
        },
        "CreatedAt": "2018-02-26T07:51:41.65482285Z",
        "UpdatedAt": "2018-02-26T14:10:43.921512677Z",
        "Spec": {
            "Name": "sample_server",
            "Labels": {
                "com.docker.stack.image": "nginx:1.13.7",
                "com.docker.stack.namespace": "sample"
            },
            "TaskTemplate": {
                "ContainerSpec": {
                    "Image": "nginx:1.13.7",
                    "Labels": {
                        "com.docker.stack.namespace": "sample"
                    },
                    "Privileges": {
                        "CredentialSpec": null,
                        "SELinuxContext": null
                    },
                    "StopGracePeriod": 10000000000,
                    "DNSConfig": {},
                    "Secrets": [
                        {
                            "File": {
                                "Name": "/etc/nginx/conf.d/default.conf",
                                "UID": "0",
                                "GID": "0",
                                "Mode": 256
                            },
                            "SecretID": "ux7vducroe1nm26re6mwa2o30",
                            "SecretName": "sample_nginx-config-v2"
                        }
                    ]
                },
                ...
```

What *can* we do, then?

## Secret names to the rescue

Thankfully for us, [version 3.5](TODO) of the Composefile schema has added the ability to define a [name for a secret](TODO) (or [config](TODO)) that is different from its key in the *YAML* file. What is even better, is that this name also supports variable substitutions! *Yay!* Using a specific name for the secret will get Docker to create it with that exact name, without prefixing it with the stack namespace or otherwise modified. Going back to the original Composefile, we only need to update the version to `3.5`, and define a name for the secret.

> You'll also have to be on Docker version `17.12.0` or higher. (TODO)

```yaml
version: '3.5'
services:

  server:
    image: nginx:1.13.7
    secrets:
      - source: nginx-config
        target: /etc/nginx/conf.d/default.conf
        mode: 0400

secrets:
  nginx-config:
    file: ./nginx.conf
    name: nginx-config-v${CONF_VERSION}
```

Let's try deploying this stack again, and declare the configuration version as `3`.

```shell
$ CONF_VERSION=3 docker stack deploy -c stack.yml sample
TODO output
$ docker secret ls
TODO secrets
$ docker service inspect sample_server
TODO inspect
```

*Great!* The update worked this time. It's up to us now, how we define the value of the variable, *anything* goes.

```shell
TODO invalid variable subst example
```

OK... within reason.

I chose to take the *MD5* checksum of the source file, and use it as a suffix on the secret names. With `bash`, it could go something like this:

```shell
$ CONF_VERSION=$(md5sum nginx.conf | tr ' ' '\n' | head -1)
$ echo "${CONF_VERSION}"
0a49b7ca11ea768b5510e6ce146c5c23
$ docker stack deploy -c stack.yml sample
...
```

I use my [webhook-proxy app](TODO) to execute a series of actions in response to an incoming webhook. One of the webhooks is from GitHub, when I push to a repo that has a stack *YAML*, defining some of the services in my [Home Lab](TODO series). The app is written in Python, and it supports extending the pipelines with custom actions, imported from external Python files. One of the steps *(actions)* is responsible for preparing the environment variables for all the secrets and configs defined in the *YAML* file, before executing the `docker stack deploy` command *(which is [running in a container](TODO link to the pipeline example in the blog-content repo), with just enough installed in it to do so)*. The relevant Python code looks like this below.

```python
TODO prep secret/config vars snippet
```

The code basically parses the *YAML*, iterates through the top-level `secrets` and `config` dictionaries, takes the filename converted into all-uppercase with underscores, which will be the name of the environment variable to be set to the *MD5* hash of the target file. We can then invoke the stack deploy command, passing in these variables.

```python
TODO with subprocess
TODO with docker.containers.run
```

This way, the name of the secret should only change, when its content changes, avoiding unnecessary service updates, but *more importantly*, eliminating manual updates to the stack *YAML* files in multiple places.

Hope this will help you as much as it has helped me! (TODO thanks with a link to the PR?)

