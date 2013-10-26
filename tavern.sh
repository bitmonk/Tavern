
#!/bin/bash
# This is a wrapper script that fires up Tavern both on Linux and OSX.
# To do so, it performs a few tests, as well as compressing files where possible.


function usage 
{
    echo "Usage: $0 {start|stop|restart} [debug/initonly]"
    echo "initonly will startup, create config files, then exit"
    echo "debug will run a single process without backgrounding"
}


function getarg 
{
# Get an argument.. Or if it doesn't exist, echo 0
# This way, we don't get "unary operator expected" errors.

    c=$1
    v=${!c}
    if [ ! -z $v ]
    then
        echo $v
    else
        echo 0
    fi
}

function since
{
# Calculate time since Variable

    ODATE=$(getarg $1)
    if [ -z $DATE ]
    then
        DATE=`date +s`
    fi
    echo $(($DATE-$ODATE))
}


function loadargs 
{
# Load in args the quick and dirty (and fast!) way

    if [ -s tmp/startup-settings ]
    then
        source tmp/startup-settings
        true > tmp/startup-settings
    fi
    DATE=`date +%s`
}

function writearg 
{
# Write out an argument
    if [ $# -eq 2 ]
    then    
        echo $1=$2 >> tmp/startup-settings
    elif [ $# -eq 1 ]
    then
        writearg $1 $(getarg $1)
    fi
}

function ramdisk
{
 # [start/stop] [dir] [size in mb]   

control=$1
mntpt=$2
size=$3

if [ "$control" == 'start' ]
then
    if [ -z "$3" ]
    then
        echo "Bad call to ramdisk"
        stop
        # Using exit, not return here, since this should abort the script.
    fi
    # Determine if we should use OSX or Linux style ramdisks
    which diskutil > /dev/null
    if [ $? -eq 0 ]
    then #OSX

        # Make sure it's not ALREADY a ramdisk
        diskutil info $mntpt | grep "Volume Name" | grep TavernRamDisk
        if [ "$?" -eq 0 ]
        then
            echo "Ramdisk already exists!"
            return
        fi
        # Calculate the size, in blocks
        disksize=$(($size*1024*1024/512))
        # Create the ramdisk
        virt_disk=`hdiutil attach -nomount ram://$disksize`
        # Verify the Ramdisk. Make extra damn sure.
        actual_size=`diskutil info $virt_disk | grep Total | awk -F'exactly ' {'print $2'} | awk {'print $1'}`
        if [ "$actual_size" != "$disksize" ]
        then
            echo "Error creating Ramdisk! - $actual_size + $disksize"
            stop
        else
            diskutil erasevolume HFS+ "TavernRamDisk-$mntpt" $virt_disk
            umount $virt_disk
            mkdir -p $mntpt
            # Union to mount locally in the FS tree
            # noowners so non-root can access
            # noauto so it doesn't mount on it's own, outside of Tavern
            # nobrowse so we don't clutter up the finder
            # noexec to head off any vulns from the local file
            # nosuid for the same reason. Not needed, so disable by default.
            # noatime since atime isn't needed, and just slows things down slightly
            mount -t hfs -o union,noowners,noauto,noexec,nosuid,noatime,nobrowse $virt_disk $mntpt
            if [ $? -eq 0 ]
                then
                echo $mntpt >> mounted
            fi
        fi
    else
        # Linux
        mkdir -p $mntpt
        mount -t tmpfs -o size="$size"M,noauto,noexec,nosuid,noatime tmpfs $mntpt
        echo $mntpt >> mounted
    fi
elif [ "$control" == "stop" ]
then
    echo "stopping disk images"
    for i in `cat tmp/mounted`
    do
        device=`mount | grep $(pwd) | grep $i|awk '{print $1}'`
        umount -f $device

        # Detect if we're on OSX, and need to remove the attached ramdisk
        which diskutil > /dev/null
        if [ $? -eq 0 ]
        then
            hdiutil detach -force $device
        fi
    done
    # We're done here.
    mv tmp/mounted tmp/mounted-old
fi
}



function stop 
{
# Stop the Tavern servers

    user=`whoami`

    for i in `ps aux | grep [w]ebfront | awk {'print $2'}`
    do
        kill $i
    done
    for i in `ps aux | grep [a]pi | awk {'print $2'}`
    do
        kill $i
    done

    # Remove ramdisks
    ramdisk stop
    exit
}

function findcommands
{
# The system commands are often different between GNU and BSD ecosystems.
# Find the versions to call.

    if [ $DEBUG -eq 1 ]
    then
        echo "Avoiding compressing JS due to debug mode.."
        yui='cat'
    else
        if [ -z "$yui" ]
        then
            # The yui-compressor will compress JS and CSS.
            # The command to run it is different on OSX and Linux, however, so figure out which one we have
            # If we don't have either, use 'cat' as an alternate 'compressor'

            echo "Testing ability to Minimize" 
            yui-compressor -h > /dev/null 2>&1
            if [ $? -eq 0 ]
            then
                yui='yui-compressor'
            fi

            yuicompressor -h  > /dev/null 2>&1
            if [ $? -eq 0 ]
            then
                yui='yuicompressor'
            fi

            if [ -z $yui ]
            then
                # No minimization
                yui='cat'
            fi

            if [ "$yui" != "cat" ]
            then 
                flags='--nomunge'
            fi
        fi
        writearg yui $yui
    fi
    # Find which version of sed we should use.
    if [ -z "$sed" ]
    then
        echo "Setting Sed."
        echo foo | gsed 's/foo/bar/' > /dev/null 2>&1
        if [ $? -eq 0 ]
        then
            #Use Gnu sed
            sed='gsed'
        else
            sed='sed'
        fi
    fi
    writearg sed $sed


    # Test our ability to take a hash
    # OSX uses md5, linux uses md5sum.
    # We will use the identifier generated in the next section

    if [ $DEBUG -eq 1 ]
    then
        echo "Using faster/less secure hashes for debug mode."
        hash='cksum'
    else
        if [ -z "$hash" ]
        then
            echo "Testing ability to hash"
            echo "foo" | md5 > /dev/null 2>&1
            if [ $? -eq 0 ]
            then
                hash='md5'
            fi
            echo "foo" | md5sum > /dev/null 2>&1
            if [ $? -eq 0 ]
            then
                hash='md5sum'
            fi
            if [ -z $hash ]
            then
                hash='cksum'
            fi
            writearg hash $hash
        fi
    fi
}


function start 
{
# Start up Tavern.

    # Save the current dir, so we can return at the end of the script
    CURDIR=`pwd`
    cd /opt/Tavern

    numservers=2
    # First, create two working directories
    mkdir -p tmp/checked
    mkdir -p tmp/unchecked
    mkdir -p tmp/gpgfiles

    mkdir -p tmp/gzipchk
    mkdir -p tmp/unchecked-gzipchk

    mkdir -p logs
    mkdir -p data/conf

    #### Ensure we're living in isolated envs, so we don't screw up the overall system
    # Ruby
    source ~/.rvm/scripts/rvm || source /etc/profile.d/rvm.sh
    rvm use system@Tavern --install --create
    # Python
    source tmp/env/bin/activate


    if [ "$1" == "debug" ]
    then
        DEBUG=1
    else
        DEBUG=0
    fi
    if [ "$1" == "initonly" ]
    then
        INITONLY=1
    else
        INITONLY=0
    fi

    # Load in the StartScript settings
    loadargs
    findcommands

    # Create necessary RamDisks
    cd tmp
    ramdisk start gpgfiles 5
    ramdisk start Robohash 20
    ramdisk start static 15
    cd ..

    echo "Ensuring Python deps are up-to-date"
    # Ensure we have the expected Python deps
    pip install -qr requirements.txt

    echo "Ensuring fontello directory compliance"


    "$sed" -i 's/\.\.\/font\//\.\.\/fonts\//g' static/css/fontello*.css
    "$sed" -i 's/margin-right: 0.2em;//g' static/css/fontello.css


    # Convert from SCSS to CSS.
    echo "Converting from SASS to CSS"

    # Remove any old and no longer used generated css files
    for i in `ls static/sass/css/`
    do
        base=`basename $i .css`
        if [ ! -f static/sass/scss/$base.scss ]
            then
            rm static/sass/css/$i
        fi
    done
    # Convert the SCSS to CSS and put in production folder
    compass compile static/sass/ -q -e production
    rsync -a static/sass/css/* static/css/


    # Go through each JS file in the project, and check to see if we've minimized it already.
    # If we haven't, minimize it. Otherwise, just skip forward, for speed.
    echo "Minimizing JS"
    mv tmp/checked/* tmp/unchecked/ > /dev/null 2>&1 
    mv tmp/gzipchk/* tmp/unchecked-gzipchk > /dev/null 2>&1 

    result=255
    for i in `find static/scripts/ -name "*.js"| grep -v '.min.js' | grep -v 'unified'`
    do
        filehash=`cat $i | $hash | cut -d" " -f 1`
        basename=`basename $i ".js"`
        if [ ! -f tmp/unchecked/$filehash.exists ]
        then
            # No pre-hashed version available
            $yui $i > static/scripts/$basename.min.js $flags
            echo "$yui $i > static/scripts/$basename.min.js $flags"
            result=$?
            echo -e "\t $basename"
            # Reformatted
        else
            : # No Reformatting needed 
            result=0
        fi
        if [ $result -eq 0 ]
        # only write the touchfile if the minimize worked
            then
            touch tmp/checked/$filehash.exists
        fi
    done

    echo "Minimizing CSS"
    for i in `find static/css/ -name "*.css"| grep -v '.min.css'`
    do
        filehash=`cat $i | $hash | cut -d" " -f 1`
        basename=`basename $i ".css"`
        if [ ! -f tmp/unchecked/$filehash.exists ]
        then
            $yui $i > static/css/$basename.min.css
            echo "$yui $i > static/css/$basename.min.css"
            echo -e "\t $basename"
            # Reformatted
        else
           # echo "Skipping $i because hash already exists at tmp/unchecked/$filehash.exists"
            : # No Reformatting needed 
        fi
        touch tmp/checked/$filehash.exists
    done

    echo "Combining CSS.."
    # No need to re-minimize the CSS, it's already OK.
    # It's faster to combine them, then to hash to see if we need to.
    for i in `ls static/css/style-*.min.css`
    do  
        STYLE=`echo style-default.min.css | awk -F- {'print $2'} |  awk -F. {'print $1'}`
        echo $i
        cat $i static/css/fontello.min.css static/css/video-js.min.css static/css/animation.min.css static/css/fonts.min.css  > static/css/unified-$STYLE.min.css
    done

    echo "Combining and further minimizing JS.."
    JSFILES="static/scripts/json3.min.js static/scripts/jquery.min.js static/scripts/mousetrap.min.js static/scripts/jstorage.min.js static/scripts/jquery.json.min.js static/scripts/colresizable.min.js static/scripts/jquery-throttle.min.js static/scripts/default.min.js static/scripts/garlic.min.js static/scripts/video.min.js static/scripts/audio.min.js static/scripts/retina.min.js"
    if [ $DEBUG -eq 0 ]
    then    

        cat $JSFILES > static/scripts/unified.js

        # It's smaller if we re-minimize afterwords. 
        filehash=`cat static/scripts/unified.js | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked/$filehash.exists ]
        then
            $yui static/scripts/unified.js > static/scripts/unified.min.js
        else
            : # No Reformatting needed 
        fi
        touch tmp/checked/$filehash.exists
    else
        # In debug mode, let's include these inline, so we can debug easier.
        echo "" > themes/default/header-debug-JS.html
        for script in $JSFILES
        do 
            # Get the basename, to avoid getting the static/tmp dir
            bn=`basename $script`
            echo "<script defer src=\"/static/scripts/$bn\"></script>" >> themes/default/header-debug-JS.html

        done
    fi

    echo "Ensuring Proper Python formatting.."
    for i in `find . -maxdepth 1 -name "*.py"`
    do
        filehash=`cat $i | $hash | cut -d" " -f 1`
        basename=`basename $i ".css"`
        if [ ! -f tmp/unchecked/$filehash.exists ]
        then
            autopep8  --in-place -p1 --aggressive $i 
            docformatter --in-place $i 
            echo -e "\t $basename"
            # Reformatted
        else
            #echo -e "\t $basename has already been checked.."
            : # No Reformatting needed 
        fi
        touch tmp/checked/$filehash.exists
    done

    ./validate.sh
    if [ "$?" -ne 0 ]
        then
        echo "Aborting due to code issue."
        stop 2
    fi

    echo "Gzipping individual files"
    # Compress the files with gzip
    for file in `find static -not -name "*.gz" -and -not -path "static/scripts/*" -and -not -path "static/css/*" -and -not -path "static/sass/*" -type f`
    do 
        filehash=`cat $file | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked-gzipchk/$filehash.exists ]
        then
            gzip --best < $file > $file.gz
            echo -e "\t $file"
            # Compressed
        else
            : # No compressing needed 
        fi
        touch tmp/gzipchk/$filehash.exists
    done


    echo "Gzipping Unified files"
    # Compress the files with gzip
    for file in `echo "static/css/unified-*.min.css static/scripts/unified.min.js" `
    do 
        filehash=`cat $file | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked-gzipchk/$filehash.exists ]
        then
            gzip --best < $file > $file.gz
            echo -e "\t $file"
            # Compressed
        else
            : # No compressing needed 
        fi
        touch tmp/gzipchk/$filehash.exists
    done

    rm tmp/unchecked-gzipchk/*.exists > /dev/null 2>&1 
    rm tmp/unchecked/*.exists > /dev/null 2>&1 


    echo "Updating Ramdisk"
    rsync -a --delete static/* tmp/static
    rsync -a --delete libs/Robohash/* tmp/Robohash

    if [ $(since lastrun) -gt 3600 ]
    then
        # Run the various functions to ensure DB caches and whatnot
        echo "Running onStart functions."
        ./ensureindex.sh
        ./TopicList.py
        ./ModList.py
        ./DiskTopics.py -l
        writearg lastrun $DATE
    else
        echo "It's only been $(($(since lastrun)/60)) minutes.. Not running onStart functions again until the hour mark."
        writearg lastrun
    fi



    echo "Starting Tavern..."
    if [ $DEBUG -eq 1 ]
    then
        python3 ./webfront.py --loglevel=DEBUG --writelog=False --debug=True
    elif [ $INITONLY -eq 1 ]
    then
        python3 ./webfront.py --initonly=True
    else    
        # -1 in the line below, since we start the count at 0, so we can be starting on 8080
        for ((i=0;i<=$((numservers -1));i++))
        do            
            port=$((8080 +i))
            echo "Starting on port $port"
            nohup python3 ./webfront.py --port=$port > logs/webfront-$port.log &
        done
        tail -n 10 logs/*
    fi
    cd $CURDIR
}


function restart 
{
    stop
    sleep 2
    start
}




if [ $# -lt 1 ]
then
    usage
    exit 1
fi

case "$1" in
        start)
            start $2
            ;;
        stop)
            stop
            ;;
        restart)
            stop
            start
            ;;
        debug|initonly)
            if [ $# -eq 1 ]
            then
                start $1
            else
                usage
            fi
            ;;
        *)
            usage
            exit 1
 
esac
