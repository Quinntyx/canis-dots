function dim
    ddcutil setvcp 10 0 --display 1 &
    ddcutil setvcp 10 0 --display 2 &
    wait
end