from __future__ import print_function

import os
import yaml
import docker
import requests

from io import BytesIO

from actions import action, Action


@action('git-update')
class GitUpdateAction(Action):
    def __init__(self, volumes):
        self.volumes = volumes

    def _run(self):
        dockerfile = """
        FROM alpine
        RUN apk add --no-cache git openssh
        """

        client = docker.DockerClient(version='auto')
        client.images.build(fileobj=BytesIO(dockerfile), rm=True, forcerm=True, tag='git-updater')

        print('Git updater image ready')

        print(client.containers.run(image='git-updater', command='git pull',
                                    remove=True, working_dir='/workdir',
                                    volumes=self.volumes))


@action('restart-changed')
class RestartChangedServicesAction(Action):
    def __init__(self, config_dir, volume_base_dir):
        self.config_dir = config_dir
        self.volume_base_dir = volume_base_dir

    def _run(self):
        for filename in self.iter_changed_files():
            for service in self.iter_related_services(filename):
                self.send_service_restart(service)

    def iter_changed_files(self):
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.md5sum'):
                original, updated = '', ''

                with open(os.path.join(self.config_dir, filename)) as original_file:
                    original = original_file.read()

                if os.path.exists(os.path.join(self.config_dir, '%s.updated' % filename)):
                    with open(os.path.join(self.config_dir, '%s.updated' % filename)) as updated_file:
                        updated = updated_file.read()

                if original != updated:
                    print('Config file changed: %s' % filename)
                    yield filename.replace('.md5sum', '')

    def iter_related_services(self, config_file):
        parsed = yaml.load(open('/etc/config/docker-stack.yml').read())

        for service, config in parsed['services'].items():
            if 'volumes' in config:
                config_path = os.path.join(self.volume_base_dir, config_file)

                if any(volume.startswith(config_path) for volume in config['volumes']):
                    yield service

    @staticmethod
    def send_service_restart(service):
        print('Restarting %s ...' % service, end=' ')
        response = requests.post('http://localhost:6002/restart/service', headers={
            'X-From': 'source',
            'X-Auth-Key': 'secret_key'
        }, json={'service': service})

        print(response)


@action('stack-deploy')
class StackDeployAction(Action):
    def __init__(self, working_dir, volumes):
        self.working_dir = working_dir
        self.volumes = volumes

    def _run(self):
        dockerfile = """
        FROM debian:stable-slim
        RUN apt-get update && apt-get -y install libltdl7
        """

        client = docker.DockerClient(version='auto')
        client.images.build(fileobj=BytesIO(dockerfile), rm=True, forcerm=True, tag='stack-deploy')

        print('Stack deploy image ready')

        print(client.containers.run(image='stack-deploy',
                                    command='docker stack deploy -c stack.yml demo',
                                    remove=True, working_dir=self.working_dir, volumes=self.volumes))
