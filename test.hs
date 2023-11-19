data List = Node Int List | Nil deriving Show

remdup:: List-> List
remdup Nil = Nil
remdup (Node x Nil) = (Node x Nil)
remdup (Node x (Node y Nil)) = if x == y then (Node x Nil) else (Node x (Node y Nil))
remdup (Node x next)
    | fst(helper next) == x = remdup(next)
    | otherwise = Node x (remdup next)


helper::List -> (Int, List)
helper (Node x next) = (x, next)
