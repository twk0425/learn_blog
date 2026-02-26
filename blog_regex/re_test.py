import re
#创建正则匹配对象
p = re.compile(r'[a-z]+')
#仅从字符串的第一个字母开始匹配
m1 = p.match('abcdefg1')
print(m1.group())
#匹配字符串从头匹配
m2=p.search('abcdefg')
#匹配字符串中所有匹配项的list[str]，以及迭代器
list_m=p.findall('abcdefg')
m3=p.finditer('abcdefg')
#m是Match[str]

m=re.match(r"(12.)(12.)","123124123")
print(m.group(0))#0为匹配的字符串(默认)，1为第1个捕获组匹配的字符串
print(m.groups())
print(m.span())#匹配的索引
print(m1.start())#匹配的开始
print(m1.end())#匹配的结尾

p = re.compile('section{ ( [^}]* ) }', re.VERBOSE)
p.sub(r'subsection{\1}','section{First} section{second}')


p = re.compile(r'\bclass\b')
print(p.search('no class at all'))