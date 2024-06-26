from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct
from aws_cdk import Stack
from modules.config import config, quotas, quotas_client
from modules.stack import GenAiStack
import logging
from ..shared.s3_access_logs_stack import S3AccessLogsStack

stack = {
    "description": "MLOps Pipeline to deploy LLM to SageMaker inference endpoint",
    "tags": {},
}



class LLMSageMakerStack(GenAiStack):
    """A root construct which represents a codepipeline CloudFormation stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        # check for required instance quate in account
        response = quotas_client.get_service_quota(
            ServiceCode="sagemaker",
            QuotaCode=quotas[config["sagemaker"]["llm_instance_type"]],
        )
        if response["Quota"]["Value"] == 0.0:
            logging.fatal(f"Please adjust your quota for the LLM Endpoint for type {config['sagemaker']['llm_instance_type']}")
            return
        else:
            print(
                f"You have enough instances quotas for the LLM Endpoint of type {config['sagemaker']['llm_instance_type']}"
            )

        repo = codecommit.Repository(
            self,
            "Repository",
            repository_name=config["appPrefix"]+"LlmSagemaker",
            code=codecommit.Code.from_directory(
                "../00_llm_endpoint_setup/codebuild/llm", branch="main"
            ),
        )
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowAllNonAdminSageMakerActions",
                    "Effect": "Allow",
                    "Action": [
                        "sagemaker:*Endpoint*"
                    ],
                    "NotResource": [
                        "arn:aws:sagemaker:*:*:domain/*",
                        "arn:aws:sagemaker:*:*:user-profile/*",
                        "arn:aws:sagemaker:*:*:app/*",
                        "arn:aws:sagemaker:*:*:space/*",
                        "arn:aws:sagemaker:*:*:flow-definition/*"
                    ]
                },
                {
                    "Sid": "AllowAWSServiceActions",
                    "Effect": "Allow",
                    "Action": [
                        "application-autoscaling:DeleteScalingPolicy",
                        "application-autoscaling:DeleteScheduledAction",
                        "application-autoscaling:DeregisterScalableTarget",
                        "application-autoscaling:DescribeScalableTargets",
                        "application-autoscaling:DescribeScalingActivities",
                        "application-autoscaling:DescribeScalingPolicies",
                        "application-autoscaling:DescribeScheduledActions",
                        "application-autoscaling:PutScalingPolicy",
                        "application-autoscaling:PutScheduledAction",
                        "application-autoscaling:RegisterScalableTarget",
                        "cloudformation:GetTemplateSummary",
                        "cloudwatch:DeleteAlarms",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:GetMetricData",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:PutMetricAlarm",
                        "cloudwatch:PutMetricData",
                        "codecommit:BatchGetRepositories",
                        "codecommit:CreateRepository",
                        "codecommit:GetRepository",
                        "codecommit:List*",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateNetworkInterfacePermission",
                        "ec2:CreateVpcEndpoint",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteNetworkInterfacePermission",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeVpcs",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:BatchGetImage",
                        "ecr:CreateRepository",
                        "ecr:Describe*",
                        "ecr:GetAuthorizationToken",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:StartImageScan",
                        "elastic-inference:Connect",
                        "iam:ListRoles",
                        "kms:DescribeKey",
                        "kms:ListAliases",
                        "logs:CreateLogDelivery",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:DeleteLogDelivery",
                        "logs:Describe*",
                        "logs:GetLogDelivery",
                        "logs:GetLogEvents",
                        "logs:ListLogDeliveries",
                        "logs:PutLogEvents",
                        "logs:PutResourcePolicy",
                        "logs:UpdateLogDelivery",
                        "tag:GetResources"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "AllowECRActions",
                    "Effect": "Allow",
                    "Action": [
                        "ecr:SetRepositoryPolicy",
                        "ecr:CompleteLayerUpload",
                        "ecr:BatchDeleteImage",
                        "ecr:UploadLayerPart",
                        "ecr:DeleteRepositoryPolicy",
                        "ecr:InitiateLayerUpload",
                        "ecr:DeleteRepository",
                        "ecr:PutImage"
                    ],
                    "Resource": [
                        "arn:aws:ecr:*:*:repository/*sagemaker*"
                    ]
                },
                {
                    "Sid": "AllowCodeCommitActions",
                    "Effect": "Allow",
                    "Action": [
                        "codecommit:GitPull",
                        "codecommit:GitPush"
                    ],
                    "Resource": [
                        "arn:aws:codecommit:*:*:*sagemaker*",
                        "arn:aws:codecommit:*:*:*SageMaker*",
                        "arn:aws:codecommit:*:*:*Sagemaker*"
                    ]
                },
                {
                    "Sid": "AllowCodeBuildActions",
                    "Action": [
                        "codebuild:BatchGetBuilds",
                        "codebuild:StartBuild"
                    ],
                    "Resource": [
                        "arn:aws:codebuild:*:*:project/sagemaker*",
                        "arn:aws:codebuild:*:*:build/*"
                    ],
                    "Effect": "Allow"
                },
                {
                    "Sid": "AllowS3ObjectActions",
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:AbortMultipartUpload"
                    ],
                    "Resource": [
                        "arn:aws:s3:::*SageMaker*",
                        "arn:aws:s3:::*Sagemaker*",
                        "arn:aws:s3:::*sagemaker*",
                    ]
                },
                {
                    "Sid": "AllowS3GetObjectWithSageMakerExistingObjectTag",
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": [
                        "arn:aws:s3:::*"
                    ],
                    "Condition": {
                        "StringEqualsIgnoreCase": {
                            "s3:ExistingObjectTag/SageMaker": "true"
                        }
                    }
                },
                {
                    "Sid": "AllowS3BucketACL",
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetBucketAcl",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": [
                        "arn:aws:s3:::*SageMaker*",
                        "arn:aws:s3:::*Sagemaker*",
                        "arn:aws:s3:::*sagemaker*"
                    ]
                },
                {
                    "Sid": "AllowCreateServiceLinkedRoleForSageMakerApplicationAutoscaling",
                    "Action": "iam:CreateServiceLinkedRole",
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/aws-service-role/sagemaker.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_SageMakerEndpoint",
                    "Condition": {
                        "StringLike": {
                            "iam:AWSServiceName": "sagemaker.application-autoscaling.amazonaws.com"
                        }
                    }
                },
                {
                    "Sid": "AllowPassRoleToSageMaker",
                    "Effect": "Allow",
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Resource": "arn:aws:iam::*:role/*",
                    "Condition": {
                        "StringEquals": {
                            "iam:PassedToService": "sagemaker.amazonaws.com"
                        }
                    }
                },
            ]
        }

        s3_access_logs = S3AccessLogsStack(
            scope=self,
            construct_id="LLMArtifactAccessLogsBucketStack"
        )

        artifacts_lifecycle_rule = s3.LifecycleRule(
            id="LLMArtifactBucketLifecycleRule",
            abort_incomplete_multipart_upload_after=Duration.days(1),
            enabled=True,
            expiration=Duration.days(360),
           # expired_object_delete_marker=True,
            transitions=[s3.Transition(
                storage_class=s3.StorageClass.GLACIER,

                transition_after=Duration.days(180),
            )]
        )

        s3_bucket = s3.Bucket(
            self,
            "LLMArtifactBucket",
            versioned=False,
            bucket_name=f"{config['appPrefixLowerCase']}-sagemaker-llm-falcon-artifact-{self.region}-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[artifacts_lifecycle_rule],
            server_access_logs_bucket=s3_access_logs.bucket
        )

        build_image = codebuild.LinuxBuildImage.STANDARD_7_0

        iam_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
                iam.ServicePrincipal("codepipeline.amazonaws.com"),
            ),
            inline_policies={
                "sagemakerPolicies": iam.PolicyDocument.from_json(policy_doc)
            }
        )

        cdk_deploy = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "SageMakerLLMEndpoint",
            build_spec=codebuild.BuildSpec.from_asset(
                "../00_llm_endpoint_setup/codebuild/llm/buildspec.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image),
            environment_variables=(
                {
                    "S3_BUCKET": codebuild.BuildEnvironmentVariable(
                        value=f"s3://{s3_bucket.bucket_name}"
                    ),
                    "MODEL_EXECUTION_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                        value=iam_role.role_arn
                    ),
                    "INSTANCE_TYPE": codebuild.BuildEnvironmentVariable(
                        value=config["sagemaker"]["llm_instance_type"]
                    ),
                    "REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                    "EXPORT_TEMPLATE_NAME": codebuild.BuildEnvironmentVariable(
                        value="exported-template.yml"
                    ),
                    "ARTIFACT_BUCKET": codebuild.BuildEnvironmentVariable(
                        value=f"s3://{s3_bucket.bucket_name}"
                    ),
                    "EXPORT_CONFIG": codebuild.BuildEnvironmentVariable(
                        value="config.json"
                    ),
                    "ENDPOINT_NAME": codebuild.BuildEnvironmentVariable(
                        value=config["appPrefix"] + config["sagemaker"]["llm_endpoint_name"]
                    ),
                }
            ),
            description="Deploy SageMaker Falcon 40B endpoint",
            timeout=Duration.minutes(120),
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
        )

        source_output = codepipeline.Artifact()

        codepipeline.Pipeline(
            self,
            "Pipeline",
            role=iam_role,
            artifact_bucket=s3_bucket,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.CodeCommitSourceAction(
                            action_name="Source",
                            output=source_output,
                            repository=repo,
                            branch="main",
                            role=iam_role,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="SageMakerLLMEndpointSetup",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="LLM",
                            project=cdk_deploy,
                            input=source_output,
                            outputs=[codepipeline.Artifact("Build")],
                            role=iam_role,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="DeployLLMSageMakerEndpoint",
                    actions=[
                        codepipeline_actions.CloudFormationCreateUpdateStackAction(
                            action_name="PrepareChanges",
                            stack_name=config["appPrefix"] + "LLMSageMakerDeployment",
                            admin_permissions=True,
                            replace_on_failure=True,
                            template_path=codepipeline.Artifact("Build").at_path(
                                "exported-template.yml"
                            ),
                            template_configuration=codepipeline.Artifact(
                                "Build"
                            ).at_path("config.json"),
                            run_order=1,
                        ),
                    ],
                ),
            ],
        )
