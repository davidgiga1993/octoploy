from unittest import TestCase

import yaml
from octoploy.k8s.BaseObj import BaseObj

from octoploy.processing.K8sObjectMerge import K8sObjectMerge


class K8sObjectMergeTest(TestCase):

    def test_append_sidecar_container(self):
        existing = '''kind: Deployment
apiVersion: v1
metadata:
  name: "${APP_NAME}"

spec:
  replicas: 1
  selector:
    name: "${APP_NAME}"
  strategy:
     type: Rolling

  template:
    metadata:
      labels:
        name: "${APP_NAME}"

    spec:
      containers:
        - name: "${APP_NAME}"
          volumeMounts:
            - name: java-cacerts-volume
              mountPath: /java/java-cacerts
'''
        new = '''
apiVersion: v1
kind: Deployment
metadata:
  name: "${APP_NAME}"
spec:
  template:
    spec:
      containers:
        - name: "sidecar-container"
'''
        merge = K8sObjectMerge()
        data = yaml.safe_load(existing)
        merge.merge(BaseObj(data), BaseObj(yaml.safe_load(new)))

        def validate(data):
            self.assertEqual('v1', data['apiVersion'])
            containers = data['spec']['template']['spec']['containers']
            self.assertEqual(2, len(containers))

            for container in containers:
                if container['name'] == '${APP_NAME}':
                    self.assertEqual(1, len(container['volumeMounts']))
                else:
                    self.assertEqual('sidecar-container', container['name'])

        validate(data)

        # Now invert the inputs, the result should be the same
        new_data = yaml.safe_load(new)
        merge.merge(BaseObj(new_data), BaseObj(yaml.safe_load(existing)))
        validate(new_data)

    def test_merge_same_container(self):
        existing = '''kind: Deployment
apiVersion: v1
metadata:
  name: "${APP_NAME}"

spec:
  replicas: 1
  selector:
    name: "${APP_NAME}"
  strategy:
     type: Rolling

  template:
    metadata:
      labels:
        name: "${APP_NAME}"

    spec:
      containers:
        - name: "${APP_NAME}"
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
          - "${APP_NAME}"
        from:
          kind: ImageStreamTag
          name: '${APP_NAME}:prod'
'''
        new = '''
apiVersion: v1
kind: Deployment
metadata:
  name: "${APP_NAME}"

spec:
  template:
    metadata:
      labels:
        name: "${APP_NAME}"

    spec:
      containers:
        - name: "${APP_NAME}"
          volumeMounts:
            - name: crawler-packages-volume
              mountPath: /packages

      volumes:
        - name: crawler-packages-volume
          persistentVolumeClaim:
            claimName: "pvc-crawler-packages"'''

        merge = K8sObjectMerge()
        data = yaml.safe_load(existing)
        merge.merge(BaseObj(data), BaseObj(yaml.safe_load(new)))

        containers = data['spec']['template']['spec']['containers']
        self.assertEqual(1, len(containers))

        container = containers[0]
        self.assertEqual(2, len(container['volumeMounts']))

        volumes = data['spec']['template']['spec']['volumes']
        self.assertEqual(2, len(volumes))
