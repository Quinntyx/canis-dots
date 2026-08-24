function bright
    ddcutil setvcp 10 100 --display 1 &
    ddcutil setvcp 10 100 --display 2 &
    wait
end