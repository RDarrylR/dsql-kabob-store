data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "${var.project_name}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${var.project_name}-ecs-task-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.project_name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${var.project_name}-ecs-task-role"
  }
}

data "aws_iam_policy_document" "ecs_task_policy" {
  # DSQL permissions scoped to multi-region cluster (primary and secondary)
  statement {
    effect = "Allow"
    actions = [
      "dsql:DbConnect",
      "dsql:DbConnectAdmin",
      "dsql:GetCluster"
    ]
    resources = [
      module.dsql_primary.arn,
      module.dsql_secondary.arn
    ]
  }

  # DSQL data operations scoped to multi-region cluster
  statement {
    effect = "Allow"
    actions = [
      "dsql-data:ExecuteStatement",
      "dsql-data:BatchExecuteStatement"
    ]
    resources = [
      "arn:aws:dsql:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster/${module.dsql_primary.identifier}",
      "arn:aws:dsql:${var.secondary_region}:${data.aws_caller_identity.current.account_id}:cluster/${module.dsql_secondary.identifier}"
    ]
  }

  # CloudWatch Logs scoped to specific log groups
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "${aws_cloudwatch_log_group.backend.arn}:*",
      "${aws_cloudwatch_log_group.frontend.arn}:*"
    ]
  }

  # Allow CreateLogGroup only for our specific log groups (if they don't exist yet)
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup"
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${var.project_name}-*"
    ]
  }
}

resource "aws_iam_policy" "ecs_task_policy" {
  name        = "${var.project_name}-ecs-task-policy"
  description = "IAM policy for ECS tasks"
  policy      = data.aws_iam_policy_document.ecs_task_policy.json

  tags = {
    Name = "${var.project_name}-ecs-task-policy"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}