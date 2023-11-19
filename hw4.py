from functools import reduce
def convert_to_decimal(bits):
    exponents = range(len(bits)-1, -1, -1)
    nums = [x[0]*(2**x[1]) for x in zip(bits, exponents)]
    return reduce(lambda acc, num: acc + num, nums)

def parse_csv(lines):
    return [(line.split(',')[0], line.split(',')[1]) for line in lines]

def unique_characters(sentence):
    return {char for char in sentence}

def squares_dict(lower_bound, upper_bound):
    return {x:x**2 for x in range(lower_bound, upper_bound+1)}

def strip_characters(sentence, chars_to_remove):
    return "".join([(lambda char: "" if char in chars_to_remove 
                    else char)(char) for char in sentence])

def func_1():
    num = 1
    def func_2():
        nonlocal num
        num += 1
        return num
    return func_2

def main():
    #print(convert_to_decimal([1, 0, 1, 1, 0]))
    #print(convert_to_decimal([1, 0, 1]))
    #print(parse_csv(["apple,8", "pear,24", "gooseberry,-2"]))
    #print(unique_characters("happy"))
    #print(squares_dict(1,5))
    #print(strip_characters("Hello, world!", {"o", "h", "l"}))
    test_func = func_1()
    print(test_func())
    print(test_func())
    print(test_func())

if __name__ == "__main__":
    main()