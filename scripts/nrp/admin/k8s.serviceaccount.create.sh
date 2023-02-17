#!/bin/zsh

NAMESPACE=c3lab
SERVICE_ACCOUNT=sched.carbonaware

# Source: https://ucsd-prp.gitlab.io/userdocs/running/scripts/

cilogon_url=$(grep cilogon ~/.kube/config | grep user: | awk '{print $2}')

kubectl create serviceaccount $SERVICE_ACCOUNT

TOKENNAME=`kubectl get serviceaccount/$SERVICE_ACCOUNT -o jsonpath='{.secrets[0].name}'`
echo $TOKENNAME
TOKEN=`kubectl get secret $TOKENNAME -o jsonpath='{.data.token}'| base64 --decode`
# echo $TOKEN

cp .kube/config .kube/config_sa.$SERVICE_ACCOUNT
kubectl --kubeconfig=.kube/config_sa.$SERVICE_ACCOUNT config set-credentials $SERVICE_ACCOUNT --token=$TOKEN
kubectl --kubeconfig=.kube/config_sa.$SERVICE_ACCOUNT config set-context --current --user=$SERVICE_ACCOUNT
kubectl --kubeconfig=.kube/config_sa.$SERVICE_ACCOUNT config view
# kubectl --kubeconfig=.kube/config_sa.$SERVICE_ACCOUNT config unset users.http://cilogon.org/server<your_cilogon_user_id>
kubectl --kubeconfig=.kube/config_sa.$SERVICE_ACCOUNT config unset users.$cilogon_url

kubectl create rolebinding ${SERVICE_ACCOUNT}_sa --clusterrole=edit --serviceaccount=$NAMESPACE:$SERVICE_ACCOUNT

kubectl --kubeconfig=.kube/config_sa.$SERVICE_ACCOUNT get pods
