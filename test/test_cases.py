# test/test_cases.py

# Should pass (single line, no spaces)
result1 = foo(a=1, b=2)
result2 = SomeClass(x=10, y=20)

# Should fail with MNA002 (single line with spaces)
result3 = foo(a = 1)
result4 = bar(x = 5, y = 10)

# Should pass (multiline with spaces)
result5 = foo(
    a = 1,
    b = 2,
)

result6 = SomeClass(
    x = 10,
    y = 20,
)

# Should fail with MNA001 (multiline without spaces)
result7 = foo(
    a=1,
    b=2,
)

# Mixed case - multiline with some correct, some wrong
result8 = foo(
    a = 1,  # correct
    b=2,    # should fail MNA001
)

# Mixed case - multiline with some correct, some wrong
result8 = bar.foo(
    a = 1,  # correct
    b=2,    # should fail MNA001
)


result9 = foo(a = 1, b=2,
              c = 3,
              )

result10 = foo(1, b=2,
               c = 3,
               )

result11 = foo(1, b=2,
               c=3,
               d = 5,
               )

result11 = foo(1,
               2,
               c=3,
               d = 5,
               )

# test/test_positional_mixed.py

# Case 1: Positional args with keyword args on same line in multiline call
# Currently this is NOT flagged by MNA003 (only checks keyword args)
result1 = foo(1, 2, a = 3,
              b = 4,
              )

# Case 2: Multiple positional args don't trigger any error
result2 = foo(1, 2, 3,
              a = 4,
              )

# Case 3: Keyword arg mixed with positional on same line
# The keyword arg `a` shares a line with positional args, but MNA003 won't flag it
# because MNA003 only counts multiple *keyword* args per line
result3 = foo(1, 2, a = 3,
              b = 4,
              )


result = foo(1, 2, a=3, b=4)

columns = [c if c.lower() != 'name' else 'otherName' for c in columns]

addDf = st.data_editor(pd.DataFrame(columns='a b c d'.split()
                                    ).reset_index().drop('index', axis=1),
                       )
