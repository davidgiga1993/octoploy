# OpenK8Deploy - Openshift/K8 templating engine
Super simple python templating engine for openshift/k8 yml files.
Detects changes made and only applies the required objects.

## Use case
This templating engine was born in the need to a very simple templating system
which can track changes (similar to terraform). 
The code should be mostly commented, although I didn't bother implementing proper logging and other utils stuff.


## Usage
### Deploy all changes
```
python deploy.py deploy-all
```

### Deploy single app
```
python deploy.py deploy nginx
```

### Deploy reload config
```
python deploy.py reload prometheus
```


## Configuration
In OK8Deploy you define apps, each app can contain multiple yml files.
Additionally, there is a project configuration which defines the OC project which should be used.

All yml files will be pre-processed before they will be imported.
This includes replacing any known `${KEY}` variables with their associate values.

### Config structure
```
configs
|- _root.yml <- Project config
|- my-app
    |- _index.yml <- App config
    |- dc.yml
    |- secrets.yml
```

### Project config
Here is a sample `_root.yml` file
```yml
project: 'my-oc-project'
```
### App config
A single app is represented by a folder containing an `_index.yml` file as well as any additional openshift yml files.
```yml
# The type defines how the app will be used.
# Can be "app" (default) or "template"
type: 'app'

# Template which should be applied, none by default
applyTemplates: []

# Templates which should be applied AFTER processing the other templates and base yml files
postApplyTemplates: []

# Indicates if this app should be deployed or ignored
enabled: true 

# Deployment config parameters
dc:
    # Name of the deployment config, available as variable, see below
    name: 'my-app'

# OPTIONAL
# Action which should be executed if a configmap has been changed
on-config-change:
# Available options: 
# deploy (re-deploys the deployment config)
  - deploy

# exec (Executes a command inside the running container)
  - exec: 
      command: /bin/sh
      args: 
        - "-c"
        - "kill -HUP $(ps a | grep prometheus | grep -v grep | awk '{print $1}')"

# Additional variables available in the template file
vars:
  NSQ_NAME: 'nsq-core'
```

### Variables
You can refer to variables in yml files by using `${VAR-NAME}`.

### Global variables
These variables are available anywhere inside the yml files

| Key | Value |
| --- | --- | 
| `DC_NAME` | Name of the deployment-config in the `_index.yml` |


### Templates
You can use templates to generate yml files for openshift.
Setting the type of an app to `template` will cause the folder to be ignored for any deployment actions.
Other apps can now refer to this template via the `templates` field. The content of a template will then be
processed using the app variables and deployed in addition to any other yml files inside the app directory.

Example:
```
|- some-template
    |- _index.yml
    |- dc.yml

|- my-app
    |- _index.yml
    |- others.yml
```

Will result in
```
|- my-app
    |- _index.yml
    |- others.yml
    |- dc.yml
```

## Change tracking
Changes are detected by storing a md5 sum in the label of the object.
If this hash changes the whole object will be applied

## Examples
### NSQ
This example adds an NSQ sidecar container to a deployment config.
The template files can be found in `examples`.

`my-app/_index.yml`
```yml
enabled: true
postApplyTemplates: [nsq-template]
vars:
  NSQ_NAME: 'app-nsq'

dc:
  name: my-app
```