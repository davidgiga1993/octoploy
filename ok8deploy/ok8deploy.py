from __future__ import annotations

import argparse

from octoploy.backup.BackupGenerator import BackupGenerator
from octoploy.config.Config import ProjectConfig, RunMode
from octoploy.deploy.AppDeploy import AppDeployment
from octoploy.utils.Log import Log

log_instance = Log('octoploy')


def load_project(config_dir: str) -> ProjectConfig:
    if config_dir != '':
        return ProjectConfig.load(config_dir)

    # No path specified, try a few common ones
    paths = ['.', 'configs', 'octoploy']
    for path in paths:
        try:
            return ProjectConfig.load(path)
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

    oc = root_config.create_oc()
    log_instance.log.info('Reloading ' + app_config.get_dc_name())
    reload_actions = app_config.get_reload_actions()
    for action in reload_actions:
        action.run(oc)
    log_instance.log.info('Done')


def _run_app_deploy(config_dir: str, app_name: str, mode: RunMode):
    root_config = load_project(config_dir)
    app_config = root_config.load_app_config(app_name)
    deployment = AppDeployment(root_config, app_config, mode)
    deployment.deploy()
    log_instance.log.info('Done')


def _run_apps_deploy(config_dir: str, mode: RunMode):
    root_config = load_project(config_dir)
    configs = root_config.load_app_configs()
    log_instance.log.info(f'Got {len(configs)} configs')
    for app_config in configs:
        AppDeployment(root_config, app_config, mode).deploy()
    log_instance.log.info('Done')


def plan_app(args):
    mode = RunMode()
    mode.plan = True
    _run_app_deploy(args.config_dir, args.name[0], mode)


def deploy_app(args):
    mode = RunMode()
    mode.out_file = args.out_file
    mode.dry_run = args.dry_run
    _run_app_deploy(args.config_dir, args.name[0], mode)


def plan_all(args):
    mode = RunMode()
    mode.plan = True
    _run_apps_deploy(args.config_dir, mode)


def deploy_all(args):
    mode = RunMode()
    mode.out_file = args.out_file
    mode.dry_run = args.dry_run
    _run_apps_deploy(args.config_dir, mode)


def create_backup(args):
    root_config = load_project(args.config_dir)
    BackupGenerator(root_config).create_backup(args.name[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('-c', '--config-dir', dest='config_dir',
                        help='Path to the folder containing all configurations',
                        default='')

    subparsers = parser.add_subparsers(help='Commands')
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
    deploy_parser.add_argument('--dry-run', dest='dry_run', help='Does not interact with openshift',
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
    if 'func' not in args.__dict__:
        parser.print_help()
        exit(1)
        return

    if args.debug:
        Log.set_debug()

    args.func(args)


if __name__ == '__main__':
    main()
