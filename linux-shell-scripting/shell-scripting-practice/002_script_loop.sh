#! /bin/bash

echo "=====================Normal For Loop============================================"

for name in Surendra Pooja Satyansh Shivansh
do
  echo "Hello $name"
done

echo "***********************C STYLE LOOP ************************"

for ((i=0;i<=10;i++))
do
echo "Index: $i"
done


echo "*********************** While Loop ************************"
count=10

while [ $count -le 15 ]
do
echo "$count"
((count++))
done


echo "************************* Until Loop***********************"

iter=1
until [ $iter -ge 5 ]
do
echo "$iter"
((iter++))
done

echo "########################### Select Loop ##############"

echo "Please select action to perform"

select option in Read Exit Quit Start Stop ?
do
echo "You selected $option"
break
done
