largest::String->String->String
largest str1 str2
    | length str1 >= length str2 = str1
    | otherwise = str2 

reflect :: Integer -> Integer
reflect 0 = 0
reflect num
    | num < 0 = (-1) + reflect (num+1)
    | num > 0 = 1 + reflect (num-1)

all_factors :: Integer->[Integer]
all_factors num = [x | x <- [1..num], num `mod` x == 0]

perfect_numbers = [x | x <- [1..], sum(init(all_factors x)) == x]

is_even :: Integer->Bool
is_even num = if num == 0 then True 
    else is_odd(num-1)

is_odd :: Integer->Bool
is_odd num = if num == 0 then False 
    else is_even(num-1)