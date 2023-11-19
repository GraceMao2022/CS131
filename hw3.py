def largest_sum(nums, k):
    if k < 0 or k > len(nums):
        raise ValueError
    elif k == 0:
        return 0
    max_sum = None
    for i in range(len(nums)-k+1):
        sum = 0
        for num in nums[i:i+k]:
            sum += num
        if max_sum == None or sum > max_sum:
            max_sum = sum
    return max_sum

def main():
    print(largest_sum([10,-8,2,6,-1,2], 4))

if __name__ == "__main__":
    main()