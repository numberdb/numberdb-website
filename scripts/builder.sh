#!/usr/bin/env bash
# The build machine, as one command.
#
#     scripts/builder.sh up        # launch and set up a builder from nothing
#     scripts/builder.sh start     # wake the stopped one
#     scripts/builder.sh stop      # park it; the disk and the image stay
#     scripts/builder.sh status    # what it is and what it costs
#     scripts/builder.sh campaign 15
#
# Setting the first one up by hand took a launch, a security group, a key
# pair, an instance profile, Docker, a 3 GB image, node, two CLIs, three
# browser logins and two portability bugs. None of that should be typed
# twice, and none of it should have to be remembered.
#
# `stop` rather than `terminate` is the default gesture: the hours cost money
# and the disk costs almost nothing, so a parked builder keeps the image it
# already pulled. The public IP changes on each start, which is why this
# rewrites the ssh config rather than leaving you to.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

PROFILE="${NUMBERDB_AWS_PROFILE:-numberdb}"
REGION="${AWS_DEFAULT_REGION:-eu-central-1}"
NAME="${NUMBERDB_BUILDER_NAME:-numberdb-builder}"
TYPE="${NUMBERDB_BUILDER_TYPE:-t3.small}"
HOSTALIAS="${NUMBERDB_BUILDER_HOST:-aws-builder}"
KEY="$HOME/.ssh/numberdb-builder.pem"

aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }
say() { printf '\n=== %s\n' "$*"; }

instance_id() {
	aws ec2 describe-instances \
		--filters "Name=tag:Name,Values=$NAME" \
		          "Name=instance-state-name,Values=pending,running,stopping,stopped" \
		--query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null
}

state_of() {
	aws ec2 describe-instances --instance-ids "$1" \
		--query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null
}

address_of() {
	aws ec2 describe-instances --instance-ids "$1" \
		--query 'Reservations[0].Instances[0].PublicIpAddress' --output text 2>/dev/null
}

wait_for() {  # instance, state
	local i
	for i in $(seq 1 40); do
		[ "$(state_of "$1")" = "$2" ] && return 0
		sleep 5
	done
	echo "gave up waiting for $1 to be $2" >&2
	return 1
}

point_ssh_at() {  # address
	local address="$1"
	python3 - "$address" "$HOSTALIAS" "$KEY" <<'PY'
import io, os, re, sys
address, alias, key = sys.argv[1:4]
path = os.path.expanduser("~/.ssh/config")
text = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
block = ("\nHost %s\n\tHostName %s\n\tUser ubuntu\n\tIdentityFile %s\n"
         "\tStrictHostKeyChecking accept-new\n\tServerAliveInterval 15\n"
         % (alias, address, key))
if re.search(r"^Host %s$" % re.escape(alias), text, re.M):
    text = re.sub(r"(Host %s\n(?:.*\n)*?\tHostName )\S+" % re.escape(alias),
                  r"\g<1>" + address, text)
else:
    text += block
io.open(path, "w", encoding="utf-8").write(text)
print("ssh config: %s -> %s" % (alias, address))
PY
	#The host key belongs to the old address; a new machine at a new address
	#is not a man in the middle.
	ssh-keygen -R "$address" >/dev/null 2>&1 || true
}

ready() {  # wait for sshd
	local i
	for i in $(seq 1 30); do
		ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOSTALIAS" true 2>/dev/null && return 0
		sleep 5
	done
	return 1
}

case "${1:-status}" in

status)
	id=$(instance_id)
	[ "$id" = "None" ] || [ -z "$id" ] && { echo "no builder exists; scripts/builder.sh up"; exit 0; }
	state=$(state_of "$id")
	type=$(aws ec2 describe-instances --instance-ids "$id" \
		--query 'Reservations[0].Instances[0].InstanceType' --output text)
	printf '%s  %s  %s  %s\n' "$id" "$type" "$state" "$(address_of "$id")"
	[ "$state" = running ] && echo "costing money; scripts/builder.sh stop when the campaign is done"
	;;

up)
	id=$(instance_id)
	if [ "$id" != "None" ] && [ -n "$id" ]; then
		echo "a builder already exists ($id); use start, or terminate it first" >&2
		exit 1
	fi
	say "finding the current Ubuntu image"
	ami=$(command aws ssm get-parameters --region "$REGION" \
		--names /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
		--query 'Parameters[0].Value' --output text)
	echo "$ami"

	say "launching $TYPE"
	id=$(aws ec2 run-instances --image-id "$ami" --instance-type "$TYPE" \
		--key-name numberdb-builder --security-groups numberdb-builder \
		--iam-instance-profile Name=numberdb-builder \
		--block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
		--tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME},{Key=project,Value=numberdb}]" \
		--query 'Instances[0].InstanceId' --output text)
	echo "$id"
	wait_for "$id" running
	point_ssh_at "$(address_of "$id")"
	ready || { echo "the machine is up but sshd is not answering" >&2; exit 1; }

	say "docker, the image, and everything it needs"
	scripts/provision-builder.sh "$HOSTALIAS"

	say "credentials, from Parameter Store rather than from a browser"
	scp -q scripts/builder-secrets.sh "$HOSTALIAS:/tmp/"
	ssh "$HOSTALIAS" "sudo apt-get install -y unzip >/dev/null 2>&1; \
		cd /tmp && curl -sS https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o a.zip \
		&& unzip -q -o a.zip && sudo ./aws/install >/dev/null 2>&1; \
		bash /tmp/builder-secrets.sh"

	say "the repository"
	ssh "$HOSTALIAS" "git clone -q https://github.com/numberdb/numberdb-website.git ~/numberdb-website 2>/dev/null; \
		cd ~/numberdb-website && mkdir -p agents/runs && git log --oneline -1"
	say "ready: scripts/builder.sh campaign 15"
	;;

start)
	id=$(instance_id); [ -n "$id" ] || { echo "no builder" >&2; exit 1; }
	aws ec2 start-instances --instance-ids "$id" >/dev/null
	wait_for "$id" running
	point_ssh_at "$(address_of "$id")"
	ready && echo "up" || echo "up, but sshd is slow; try again in a moment"
	;;

stop)
	id=$(instance_id); [ -n "$id" ] || { echo "no builder" >&2; exit 1; }
	#Save the refreshed sessions first: they are newer on the machine than in
	#Parameter Store, and a stale refresh token means a browser login.
	ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOSTALIAS" \
		"bash ~/numberdb-website/scripts/builder-secrets.sh --save" 2>/dev/null || \
		echo "(could not save credentials back; stopping anyway)"
	aws ec2 stop-instances --instance-ids "$id" >/dev/null
	echo "stopping; the disk and the image stay"
	;;

campaign)
	shift
	count="${1:-2}"
	id=$(instance_id); [ -n "$id" ] || { echo "no builder" >&2; exit 1; }
	[ "$(state_of "$id")" = running ] || { echo "the builder is not running; scripts/builder.sh start" >&2; exit 1; }
	stamp=$(date -u +%Y%m%dT%H%M%SZ)
	ssh "$HOSTALIAS" "cd ~/numberdb-website && git pull -q 2>/dev/null; \
		[ -f ~/.numberdb-gh ] && . ~/.numberdb-gh; export GH_TOKEN; \
		NUMBERDB_CAMPAIGN='$stamp' NUMBERDB_WRITER=codex NUMBERDB_REMOTE=local \
		NUMBERDB_SAGE_IMAGE=numberdb/builder:latest NUMBERDB_SAGE_PYTHONPATH= \
		NUMBERDB_SAGE_MEMORY=1200m NUMBERDB_KEY=\$HOME/.config/numberdb/zeta3-key \
		setsid nohup agents/campaign.sh $count > agents/runs/campaign-$stamp.log 2>&1 < /dev/null & \
		sleep 3; echo 'started campaign $stamp'"
	echo "watch it with: ssh $HOSTALIAS 'tail -f ~/numberdb-website/agents/runs/campaign-$stamp.log'"
	;;

*)
	echo "usage: $0 {up|start|stop|status|campaign N}" >&2
	exit 2
	;;
esac
