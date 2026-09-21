"""
Unit tests for Phase 11.3: Docker Compose & Kubernetes Manifests verification.
"""

import os
import pytest
import yaml

def test_docker_compose_manifest():
    compose_path = "deploy/docker-compose.yml"
    assert os.path.exists(compose_path), "docker-compose.yml should exist"
    
    with open(compose_path, "r") as f:
        data = yaml.safe_load(f)
        
    assert "version" in data or "services" in data
    services = data.get("services", {})
    assert "pqc-gateway" in services
    
    gateway_svc = services["pqc-gateway"]
    assert "ports" in gateway_svc
    assert "8090:8090" in gateway_svc["ports"]
    assert "environment" in gateway_svc

def test_k8s_deployment_manifest():
    deploy_path = "deploy/k8s/deployment.yaml"
    assert os.path.exists(deploy_path), "deployment.yaml should exist"
    
    with open(deploy_path, "r") as f:
        docs = list(yaml.safe_load_all(f))
        
    assert len(docs) > 0
    deployment = docs[0]
    assert deployment["kind"] == "Deployment"
    assert deployment["metadata"]["name"] == "pqc-gateway-deployment"
    
    spec = deployment["spec"]
    containers = spec["template"]["spec"]["containers"]
    assert len(containers) > 0
    container = containers[0]
    assert container["name"] == "pqc-gateway"
    assert container["ports"][0]["containerPort"] == 8090

def test_k8s_service_manifest():
    svc_path = "deploy/k8s/service.yaml"
    assert os.path.exists(svc_path), "service.yaml should exist"
    
    with open(svc_path, "r") as f:
        svc = yaml.safe_load(f)
        
    assert svc["kind"] == "Service"
    assert svc["metadata"]["name"] == "pqc-gateway-service"
    assert svc["spec"]["ports"][0]["port"] == 80
    assert svc["spec"]["ports"][0]["targetPort"] == 8090

def test_k8s_ingress_manifest():
    ingress_path = "deploy/k8s/ingress.yaml"
    assert os.path.exists(ingress_path), "ingress.yaml should exist"
    
    with open(ingress_path, "r") as f:
        ingress = yaml.safe_load(f)
        
    assert ingress["kind"] == "Ingress"
    assert ingress["metadata"]["name"] == "pqc-gateway-ingress"
    rules = ingress["spec"]["rules"]
    assert len(rules) > 0
    backend = rules[0]["http"]["paths"][0]["backend"]
    assert backend["service"]["name"] == "pqc-gateway-service"
    assert backend["service"]["port"]["number"] == 80
