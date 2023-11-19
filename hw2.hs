scale_nums::[Integer]->Integer->[Integer]
scale_nums lst factor = 
    map (factor*) lst

only_odds::[[Integer]]->[[Integer]]
only_odds lst = 
    filter (\x -> all (\y -> y `mod` 2 /= 0) x) lst

largest_in_list::[String]->String
largest_in_list lst = foldl largest "" lst

largest :: String -> String -> String
largest first second =
    if length first >= length second then first else second

count_if::(a -> Bool) -> [a] -> Integer
count_if func [] = 0
count_if func (x:xs)
    | func x = count_if func xs + 1
    | otherwise = count_if func xs

count_if_with_fold::(a -> Bool) -> [a] -> Integer
count_if_with_fold func lst = 
    foldl (\accum x -> if func x then accum + 1 else accum) 0 lst

f a b =
    let c = \a -> a -- (1) //1
        d = \c -> b -- (2)
    in \e f -> c d e -- (3) 


data LinkedList = EmptyList | ListNode Integer LinkedList
    deriving Show

ll_contains::LinkedList -> Integer -> Bool
ll_contains EmptyList val = False
ll_contains (ListNode num ll) val
    | num == val = True
    | otherwise = ll_contains ll val

ll_insert::LinkedList -> Integer -> Integer -> LinkedList
ll_insert EmptyList index val = (ListNode val EmptyList)
ll_insert (ListNode num ll) index val
    | index <= 0 = (ListNode val (ListNode num ll))
    | otherwise = (ListNode num (ll_insert ll (index-1) val))

longest_run::[Bool] -> Integer
longest_run lst = 
    snd (foldl (\(currCount, maxCount) y -> 
        if y then (currCount+1, max (currCount+1) maxCount) else (0, maxCount)) (0, 0) lst)

data Tree = Empty | Node Integer [Tree]
max_tree_value::Tree -> Integer
max_tree_value Empty = 0
max_tree_value (Node num treeLst) =
    foldl max num (map max_tree_value treeLst)