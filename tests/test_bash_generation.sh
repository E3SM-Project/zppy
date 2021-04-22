cd ..
python zppy/post.py -c tests/test_bash_generation.cfg
ls test_output/post/scripts
# https://stackoverflow.com/questions/2019857/diff-files-present-in-two-different-directories
diff -bur test_output/post/scripts tests/expected_output
echo $?
rm -r test_output
