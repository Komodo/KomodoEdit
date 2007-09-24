struct EmptyClassA {};
class EmptyClassB {};

class BaseClass: EmptyClassA, EmptyClassB {
    public:
        int foo(int a);
};

int a_function(float f, EmptyClassA e)
{
}

int main(void)
{
  return 0;
}

