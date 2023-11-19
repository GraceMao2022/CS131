from intbase import InterpreterBase, ErrorType
from brewparse import parse_program

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
    def run(self, program):
        ast = parse_program(program)         # parse program into AST
        self.variable_name_to_value = {}  # dict to hold variables
        
        main_func_node = self.get_main_func_node(ast)
       
        #if there exists a main function
        if main_func_node:
            self.run_main_func(main_func_node)
        else: #throw error since no main
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )
    
    #get main func node, return None if no main
    def get_main_func_node(self, ast):
        functions = ast.get("functions")
        for func in functions:
            if func.get("name") == "main":
                return func
        return None
    
    def evaluate_func_definitions(self, ast):
        functions = ast.get("functions")
        

    def run_main_func(self, func_node):
        func_statements = func_node.get("statements")
        #run each statement in main function
        for statement in func_statements:
            self.run_statement(statement)

    def run_statement(self, statement_node):
        if statement_node.elem_type == '=':
            self.do_assignment(statement_node)
        elif statement_node.elem_type == 'fcall':
            self.do_func_call(statement_node)
        elif statement_node.elem_type == 'if':
            self.evaluate_if_statement(statement_node)
        elif statement_node.elem_type == 'while':
            self.evaluate_while_statement(statement_node)
        elif statement_node.elem_type == 'return':
            self.evaluate_return_statement(statement_node)


    def do_assignment(self, statement_node):
        target_var_name = statement_node.get("name")
        source_node = statement_node.get("expression")
        resulting_value = self.evaluate_statement(source_node)
        #assign variable (new or old) to resulting value after evaluate statement
        self.variable_name_to_value[target_var_name] = resulting_value

    def do_func_call(self, func_node):
        func_to_be_called = func_node.get('name')

        #print function
        if func_to_be_called == 'print':
            self.do_print(func_node.get('args'))
        #inputi fuction
        elif func_to_be_called == 'inputi':
            return self.do_input(func_node.get('args'))
        else: #unknown function
            super().error(ErrorType.NAME_ERROR,
                        f"Unknown function {func_to_be_called}")
    
    def evaluate_if_statement(self, if_node):
        condition = if_node.get('condition')
        true_statements = if_node.get('statements')
        false_statements = if_node.get('else_statements')
        #check if condition is boolean expression
        result = self.evaluate_expression(condition)
        if result:
            for statement in true_statements:
                self.run_statement(statement)
        else:
            for statement in false_statements:
                self.run_statement(statement)

    def evaluate_while_statement(self, while_node):
        condition = while_node.get('condition')
        statements = while_node.get('statements')
        #check if condition is boolean expression
        while(self.evaluate_expression(condition)):
            for statement in statements:
                self.run_statement(statement)

    def evaluate_return_statement(self, return_node):
        expression = return_node
        if expression is None:
            return None
        return self.evaluate_expression(expression)
    
    def evaluate_expression(self, expression_node):
        #if expression is function call
        if expression_node.elem_type == 'fcall':
            return self.do_func_call(expression_node)
        elif expression_node.elem_type == 'neg' or expression_node.elem_type == '!':
            return self.evaluate_unary_op(expression_node)
        #if expression is variable
        elif expression_node.elem_type == 'var':
            return self.evaluate_variable(expression_node)
        #if expression is value
        elif (expression_node.elem_type == 'int' or expression_node.elem_type == 'string' or
            expression_node.elem_type == 'bool' or expression_node.elem_type == 'nil'):
            return self.evaluate_value(expression_node)
        #if expression is binary operator
        else:
            return self.evaluate_binary_operator(expression_node)

    def evaluate_binary_operator(self, binary_expression):
        op1 = binary_expression.get('op1')
        op2 = binary_expression.get('op2')
        
        #evaluate opt1
        op1_value = self.evaluate_statement(op1)
        #evaluate op2
        op2_value = self.evaluate_statement(op2)

        #arithmetic with numbers
        if type(op1_value) is int and type(op2_value) is int:
            if binary_expression.elem_type == '+':
                return op1_value + op2_value
            elif binary_expression.elem_type == '-':
                return op1_value - op2_value
        else:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for arithmetic operation",
            )

    #def evaluate_unary_op(self, unary_node):

    def evaluate_variable(self, variable_node):
        var_name = variable_node.get('name')
        #if variable exists in dictionary
        if var_name in self.variable_name_to_value:
            return self.variable_name_to_value[var_name]
        else:
            super().error(ErrorType.NAME_ERROR,
                        f"Variable {var_name} has not been defined",)
    
    def evaluate_value(self, value_node):
        return value_node.get('val')
            
    def evaluate_arg(self, arg_node):
        return

    def do_print(self, args):
        print_string = ""
        #concatenate each argument for print() to output string
        for arg in args:
            arg_val = self.evaluate_statement(arg)
            print_string = print_string + str(arg_val)
            
        super().output(print_string)

    def do_input(self, args):
        #if length of arg > 1, throw error
        if len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR,
                f"No inputi() function found that takes > 1 parameter",
            )
            
        #print prompt if there is one
        if len(args) == 1:
            prompt = args[0]
            super().output(self.evaluate_value(prompt))
        
        user_input = super().get_input()
        return int(user_input) #return input cast to int

def main():
    interpreter = Interpreter()
    program1 = """func main() { /* a function that computes the sum of two numbers */
    num = 1;
    num = "hi";
    print(hi);
    }
    """
    interpreter.run(program1)

if __name__ == "__main__":
    main()