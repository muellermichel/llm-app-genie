from dataclasses import dataclass
from typing import Sequence

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from modules.ssm_parameter_reader import SSMParameterReader, SSMParameterReaderProps
from modules.stack import GenAiStack
from stacks.shared.vpc_peering_stack import VPCPeeringStack

stack = {
    "description": "VPC for private OpenSearch domains",
    "tags": {},
}


@dataclass
class OpenSearchPrivateVPCStackOutput:
    vpc: ec2.IVpc
    subnet_selection: ec2.SubnetSelection


class OpenSearchPrivateVPCStack(GenAiStack):
    output_props: OpenSearchPrivateVPCStackOutput

    # def __init__(self, scope: Construct, construct_id: str, config: Config, **kwargs) -> None:
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc_id_ssm_param: str,
        peering_vpc_id_ssm_parameter_name: str,
        peering_vpc_cidr: str,
        peer_region: str,
        peering_connection_ssm_parameter_name: str,
        cidr_range: str = "10.4.0.0/16",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        private_subnet = ec2.SubnetConfiguration(
            name="Private", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24
        )

        public_subnet = ec2.SubnetConfiguration(
            name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
        )

        private_with_egress_subnet = ec2.SubnetConfiguration(
            name="PrivateWithEgress", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24
        )

        vpc = ec2.Vpc(
            scope=self,
            id="OpenSearchVPC",
            ip_addresses=ec2.IpAddresses.cidr(cidr_range),
            max_azs=3,
            nat_gateway_provider=ec2.NatProvider.gateway(),
            nat_gateways=1,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[private_subnet, private_with_egress_subnet, public_subnet],
            flow_logs={
                "cloudwatch":ec2.FlowLogOptions(
                    destination=ec2.FlowLogDestination.to_cloud_watch_logs()
                # Use default configuration. See also https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/FlowLogOptions.html#aws_cdk.aws_ec2.FlowLogOptions
            )
            }
        )

        opensearch_subnets = vpc.private_subnets + vpc.isolated_subnets

        subnet_selection = ec2.SubnetSelection(subnets=opensearch_subnets)

        ssm.StringParameter(
            self,
            "OpenSearchVPCIdParameter",
            parameter_name=vpc_id_ssm_param,
            description="VPC id of OpenSearch vpc.",
            string_value=vpc.vpc_id,
        )

        self.output_props = OpenSearchPrivateVPCStackOutput(
            vpc=vpc, subnet_selection=subnet_selection
        )

        peer_vpc_id_reader = SSMParameterReader(
            self,
            "VPCPerringVPCIdReader",
            props=SSMParameterReaderProps(
                parameter_name=peering_vpc_id_ssm_parameter_name, region=peer_region
            ),
        )
        peering_vpc_id = peer_vpc_id_reader.get_parameter_value()

        opensearch_vpc_peering_stack = VPCPeeringStack(
            self,
            "OpenSearchVPCPeering",
            peering_vpc_id,
            peering_vpc_cidr,
            peer_region,
            vpc.vpc_id,
            vpc_route_table_ids=[
                subnet.route_table.route_table_id for subnet in opensearch_subnets
            ],
            peering_connection_ssm_parameter_name=peering_connection_ssm_parameter_name,
        )

    @property
    def output(self) -> OpenSearchPrivateVPCStackOutput:
        return self.output_props
