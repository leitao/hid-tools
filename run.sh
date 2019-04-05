set -ex
git reset --hard

for i in $(find . -name \*py)
do
	echo "XXXXXXXX"
	echo $i
	echo "XXXXXXXX"
	~/Devel/unf/unf.py $i > foo
	cp foo $i
done
