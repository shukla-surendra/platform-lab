#! /opt/homebrew/bin/bash
get_enevironment_name() {
  echo "dev"
}

env=$(get_enevironment_name)

if [ "$env" = "dev" ]
then
echo "This is development environment"
elif [ "$env" = "staging" ]
then
echo "This is staging environment"
elif [ "$env" = "prod" ]
then
echo "This is production environment"
else
echo "This is unknown environment"
fi