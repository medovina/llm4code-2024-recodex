main = do
    xs <- getLine
    ys <- getLine
    print ((read xs :: Int) + (read ys :: Int))
