

for f1 in $1/*_For_FALCON; do
    f2=${f1}_REFERENCE

    echo Sequence:   $f1
    echo Reference:  $f2
    echo Gate Index: $2 

    falcon-cardiac -rfd $f2 -sfd $f1 -gi $2
    
done
