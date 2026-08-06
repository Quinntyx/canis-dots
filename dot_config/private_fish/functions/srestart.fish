function srestart --wraps killall
    echo "Restarting $argv[1]..."
    killall $argv[1]
    srun $argv[1]
    echo "Done!"
end