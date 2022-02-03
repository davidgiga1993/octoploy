from unittest import TestCase

import yaml

from octoploy.processing.OcObjectMerge import OcObjectMerge


class OcObjectMergeTest(TestCase):

    def test_append_sidecar_container(self):
        existing = '''kind: DeploymentConfig
apiVersion: v1
metadata:
  name: "${DC_NAME}"

spec:
  replicas: 1
  selector:
    name: "${DC_NAME}"
  strategy:
     type: Rolling

  template:
    metadata:
      labels:
        name: "${DC_NAME}"

    spec:
      containers:
        - name: "${DC_NAME}"
          volumeMounts:
            - name: java-cacerts-volume
              mountPath: /java/java-cacerts
'''
        new = '''
kind: DeploymentConfig
spec:
  template:
    spec:
      containers:
        - name: "sidecar-container"
'''
        merge = OcObjectMerge()
        data = yaml.safe_load(existing)
        merge.merge(data, yaml.safe_load(new))

        def validate(data):
            self.assertEqual('v1', data['apiVersion'])
            containers = data['spec']['template']['spec']['containers']
            self.assertEqual(2, len(containers))

            for container in containers:
                if container['name'] == '${DC_NAME}':
                    self.assertEqual(1, len(container['volumeMounts']))
                else:
                    self.assertEqual('sidecar-container', container['name'])

        validate(data)

        # Now invert the inputs, the result should be the same
        new_data = yaml.safe_load(new)
        merge.merge(new_data, yaml.safe_load(existing))
        validate(new_data)

    def test_merge_same_container(self):
        existing = '''kind: DeploymentConfig
apiVersion: v1
metadata:
  name: "${DC_NAME}"

spec:
  replicas: 1
  selector:
    name: "${DC_NAME}"
  strategy:
     type: Rolling

  template:
    metadata:
      labels:
        name: "${DC_NAME}"

    spec:
      containers:
        - name: "${DC_NAME}"
          imagePullPolicy: Always
          resources:
            requests:
              cpu: "20m"
              memory: "10Mi"
            limits:
              memory: "300Mi"
          envFrom: 
            - configMapRef:
                name: ms-config
            - secretRef:
                name: ms-secrets

          volumeMounts:
            - name: java-cacerts-volume
              mountPath: /java/java-cacerts

      volumes:
        - name: java-cacerts-volume
          configMap:
            name: java-cacerts

  triggers:
    - type: ConfigChange
    - type: ImageChange
      imageChangeParams:
        automatic: true
        containerNames:
          - "${DC_NAME}"
        from:
          kind: ImageStreamTag
          name: '${DC_NAME}:prod'
'''
        new = '''
kind: DeploymentConfig
metadata:
  name: "${DC_NAME}"

spec:
  template:
    metadata:
      labels:
        name: "${DC_NAME}"

    spec:
      containers:
        - name: "${DC_NAME}"
          volumeMounts:
            - name: crawler-packages-volume
              mountPath: /packages

      volumes:
        - name: crawler-packages-volume
          persistentVolumeClaim:
            claimName: "pvc-crawler-packages"'''

        merge = OcObjectMerge()
        data = yaml.safe_load(existing)
        merge.merge(data, yaml.safe_load(new))

        containers = data['spec']['template']['spec']['containers']
        self.assertEqual(1, len(containers))

        container = containers[0]
        self.assertEqual(2, len(container['volumeMounts']))

        volumes = data['spec']['template']['spec']['volumes']
        self.assertEqual(2, len(volumes))
