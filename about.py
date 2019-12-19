import os

fluentd_ip = 'host'
fluentd_port = 24224

if os.environ.get('FLUENTD_IP_PORT'):
    fluentd_ip_port = os.environ.get("FLUENTD_IP_PORT").split(":")
    fluentd_ip = fluentd_ip_port[0]
    fluentd_port = int(fluentd_ip_port[1])

properties = {
    "name": "estuary-deployer",
    "version": "4.0.1",
    "description": "estuary-deployer",
    "author": "Catalin Dinuta",
    "platforms": ["Linux", "Mac"],
    "license": "Apache-2.0",
    "port": 8080,
    "fluentd_ip": fluentd_ip,
    "fluentd_port": fluentd_port
}
