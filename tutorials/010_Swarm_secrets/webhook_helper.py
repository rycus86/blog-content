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
    def __init__(self, stack_name, working_dir, config_dir, volumes, stack_file='stack.yml', user=None):
        self.stack_name = stack_name
        self.working_dir = working_dir
        self.config_dir = config_dir
        self.volumes = volumes
        self.stack_file = stack_file
        self.user = user

    def _run(self):
        dockerfile = """
        FROM debian:stable-slim
        RUN apt-get update && apt-get -y install libltdl7
        """

        stack_name = self._render_with_template(self.stack_name)
        working_dir = self._render_with_template(self.working_dir)
        config_dir = self._render_with_template(self.config_dir)
        stack_file = self._render_with_template(self.stack_file)
        volumes = list(map(self._render_with_template, self.volumes))

        volumes.append('%s:%s:ro' % (working_dir, working_dir))

        client = docker.DockerClient(version='auto')
        client.images.build(fileobj=BytesIO(dockerfile), rm=True, forcerm=True, tag='stack-deploy')

        print('Stack deploy image ready')

        secret_versions = {
            key: value
            for key, value in self._prepare_secret_versions(config_dir, stack_file)
        }

        print(client.containers.run(
            image='stack-deploy',
            command='docker stack deploy -c %s --resolve-image=always --with-registry-auth %s' %
                    (stack_file, stack_name),
            user=self.user, working_dir=working_dir,
            environment=secret_versions,
            volumes=volumes, remove=True)
        )

        client.api.close()

    def _prepare_secret_versions(self, working_dir, stack_file):
        with open('%s/%s' % (working_dir, stack_file)) as stack_yml:
            parsed = yaml.load(stack_yml.read())

            for variable, version in self._prepare_versions_for('configs', parsed, working_dir):
                yield variable, version

            for variable, version in self._prepare_versions_for('secrets', parsed, working_dir):
                yield variable, version

    @staticmethod
    def _prepare_versions_for(root_key, parsed, working_dir):
        if root_key not in parsed:
            return

        for key, config in parsed[root_key].items():
            path = config.get('file')
            if not path:
                continue

            path = os.path.join(working_dir, path)
            if os.path.exists(path):
                with open(path, 'rb') as secret_file:
                    version = hashlib.md5(secret_file.read()).hexdigest()

                variable = os.path.basename(path).upper()
                variable, _ = re.subn('[^A-Z0-9_]', '_', variable)

                yield variable, version
