function on --description 'Wake the focused monitor from DDC standby'
    ddcutil --display 1 --noverify setvcp D6 01
    ddcutil --display 2 --noverify setvcp D6 01
end
