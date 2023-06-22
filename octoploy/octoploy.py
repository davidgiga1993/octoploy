from __future__ import annotations

import argparse

from octoploy.backup.BackupGenerator import BackupGenerator
from octoploy.config.Config import RootConfig, RunMode
from octoploy.deploy.AppDeploy import AppDeployment
from octoploy.processing.DecryptionProcessor import DecryptionProcessor
from octoploy.state.StateMover import StateMover
from octoploy.utils.Encryption import YmlEncrypter
from octoploy.utils.Log import Log

log_instance = Log('octoploy')


def load_project(config_dir: str) -> RootConfig:
    if config_dir != '':
        return RootConfig.load(config_dir)

    # No path specified, try a few common ones
    paths = ['.', 'configs', 'octoploy']
    for path in paths:
        try:
            return RootConfig.load(path)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f'Did not find config in any of {paths}')


def reload_config(args):
    root_config = load_project(args.config_dir)
    app_config = root_config.load_app_config(args.name[0])
    if not app_config.enabled():
        log_instance.log.error('App is disabled')
        return
    if app_config.is_template():
        log_instance.log.error('App is a template')
        return

    oc = root_config.create_api()
    log_instance.log.info('Reloading ' + app_config.get_name())
    reload_actions = app_config.get_reload_actions()
    for action in reload_actions:
        action.run(oc)
    log_instance.log.info('Done')


def _run_app_deploy(config_dir: str, app_name: str, mode: RunMode):
    root_config = load_project(config_dir)
    root_config.initialize_state(mode)
    app_config = root_config.load_app_config(app_name)
    try:
        deployment = AppDeployment(root_config, app_config, mode)
        deployment.deploy()
    finally:
        root_config.persist_state(mode)
    log_instance.log.info('Done')


def _run_apps_deploy(config_dir: str, mode: RunMode):
    root_config = load_project(config_dir)
    root_config.initialize_state(mode)
    configs = root_config.load_app_configs()
    log_instance.log.debug(f'Found {len(configs)} apps to deploy')
    try:
        for app_config in configs:
            AppDeployment(root_config, app_config, mode).deploy()
    finally:
        root_config.persist_state(mode)
    log_instance.log.info('Done')


def plan_app(args):
    mode = RunMode()
    mode.plan = True
    mode.set_override_env(args.env)
    _run_app_deploy(args.config_dir, args.name[0], mode)


def deploy_app(args):
    mode = RunMode()
    mode.out_file = args.out_file
    mode.dry_run = args.dry_run
    mode.set_override_env(args.env)
    _run_app_deploy(args.config_dir, args.name[0], mode)


def plan_all(args):
    mode = RunMode()
    mode.plan = True
    mode.set_override_env(args.env)
    _run_apps_deploy(args.config_dir, mode)


def deploy_all(args):
    mode = RunMode()
    mode.out_file = args.out_file
    mode.dry_run = args.dry_run
    mode.set_override_env(args.env)
    _run_apps_deploy(args.config_dir, mode)


def create_backup(args):
    root_config = load_project(args.config_dir)
    BackupGenerator(root_config).create_backup(args.name[0])


def encrypt_secrets(args):
    files = args.file
    for file in files:
        YmlEncrypter(file).encrypt()


def list_state(args):
    root_config = load_project(args.config_dir)
    root_config.initialize_state(RunMode())

    state = root_config.get_state()
    state.print()


def move_state(args):
    source = args.items[0]
    dest = args.items[1]
    target_cm = args.to

    root_config = load_project(args.config_dir)
    mover = StateMover(root_config)
    mover.move(source, dest, dest_configmap=target_cm)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', dest='version', action='store_true',
                        help='Prints the current version')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='Enables debug logging')
    parser.add_argument('--skip-secrets', dest='skip_secrets', action='store_true',
                        help="Skips all secret objects and therefore doesn't require a key to be set")
    parser.add_argument('--deploy-plain-secrets', dest='deploy_plain_text', action='store_true',
                        help="Deploys plain text secret objects")
    parser.add_argument('-c', '--config-dir', dest='config_dir',
                        help='Path to the folder containing all configurations',
                        default='')
    parser.add_argument('-e', '--env', dest='env', action='append',
                        help='key=value pairs of parameters to set/override during for the templating engine',
                        default=[])

    subparsers = parser.add_subparsers(help='Commands')
    state_parser = subparsers.add_parser('state', help='State interactions')

    state_subparsers = state_parser.add_subparsers(help='State commands')
    state_list_parser = state_subparsers.add_parser('list')
    state_list_parser.set_defaults(func=list_state)

    state_mv_parser = state_subparsers.add_parser('mv')
    state_mv_parser.set_defaults(func=move_state)

    state_mv_parser.add_argument('items', help='Source and destination.\n'
                                               'The format for an object is: octoployName/Namespace/k8sFqn\n'
                                               'For example: "my-old-app/Namespace2/k8sFqn" '
                                               '"my-new-app/Namespace2/k8sFqn"', nargs=2)
    state_mv_parser.add_argument('--to', dest='to', help='Configmap where the state should be moved to (optional).'
                                                         'Format: configmapSuffix|namespace/configmapSuffix')
    state_mv_parser.set_defaults(func=move_state)

    encrypt_parser = subparsers.add_parser('encrypt', help='Encrypts k8s secrets objects')
    encrypt_parser.add_argument('file', help='Yml file to be encrypted', nargs=1)
    encrypt_parser.set_defaults(func=encrypt_secrets)

    backup_parser = subparsers.add_parser('backup', help='Creates a backup of all resources in the cluster')
    backup_parser.add_argument('name', help='Name of the backup folder', nargs=1)
    backup_parser.set_defaults(func=create_backup)

    reload_parser = subparsers.add_parser('reload', help='Reloads the configuration of a running application')
    reload_parser.add_argument('name', help='Name of the app which should be reloaded (folder name)', nargs=1)
    reload_parser.set_defaults(func=reload_config)

    plan_parser = subparsers.add_parser('plan', help='Verifies what changes have to be applied for a single app')
    plan_parser.add_argument('name', help='Name of the app which should be checked (folder name)', nargs=1)
    plan_parser.set_defaults(func=plan_app)

    plan_all_parser = subparsers.add_parser('plan-all',
                                            help='Verifies what changes have to be applied for all apps')
    plan_all_parser.set_defaults(func=plan_all)

    deploy_parser = subparsers.add_parser('deploy', help='Deploys the configuration of an application')
    deploy_parser.add_argument('--out-file', dest='out_file',
                               help='Writes all objects into a yml file instead of deploying them. '
                                    'This does not communicate with openshift in any way')
    deploy_parser.add_argument('--dry-run', dest='dry_run', help='Does not interact with k8s/openshift '
                                                                 '(pure template processing). '
                                                                 'Can be used in conjunction with out-file to preview '
                                                                 'templates',
                               action='store_true')
    deploy_parser.add_argument('name', help='Name of the app which should be deployed (folder name)', nargs=1)
    deploy_parser.set_defaults(func=deploy_app)

    deploy_all_parser = subparsers.add_parser('deploy-all',
                                              help='Deploys all objects of all enabled application')
    deploy_all_parser.add_argument('--out-file', dest='out_file',
                                   help='Writes all objects into a yml file instead of deploying them. '
                                        'This does not communicate with openshift in any way')
    deploy_all_parser.add_argument('--dry-run', dest='dry_run', help='Does not interact with openshift',
                                   action='store_true')
    deploy_all_parser.set_defaults(func=deploy_all)

    args = parser.parse_args()
    if args.version:
        from octoploy import __version__
        print(f'Octoploy {__version__}')
        return

    if 'func' not in args.__dict__:
        parser.print_help()
        exit(1)
        return

    if args.debug:
        Log.set_debug()

    DecryptionProcessor.skip_secrets = args.skip_secrets
    DecryptionProcessor.deploy_plain_text = args.deploy_plain_text
    args.func(args)


if __name__ == '__main__':
    main()
