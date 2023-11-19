from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from collections import defaultdict
import copy

class Function:
    def __init__(self, function_node):
        self.function_node = function_node
        self.num_args = len(function_node.get("args"))
        self.func_name = function_node.get("name")

class Lambda:
    def __init__(self, lambda_node, closure_vars, interpreter_instance):
        self.lambda_node = lambda_node
        self.closure_vars = closure_vars #variables captured at time of lambda construction
        self.parameters = lambda_node.get('args')
        self.statements = lambda_node.get('statements')
        self.inter_instance = interpreter_instance #to access Interpreter methods and member variables

    #run lambda using input args
    def run_lambda(self, input_args):
        local_vars = set() #variables that go out of scope once lambda ends
        self.arg_names = set() #stores names of the parameter variables

        #if passing in mismatching arguments, throw error
        if len(input_args) != len(self.parameters):
            self.inter_instance.throw_unknown_lambda_error(len(input_args))
            
        #deal with parameters first
        for i in range(len(self.parameters)):
            arg = self.parameters[i]
            arg_name = arg.get('name')
            self.arg_names.add(arg_name)
            input_arg = input_args[i]
            local_vars.add(arg_name) #add arg as local variable

            #if arg variable has not been created before
            if arg_name not in self.inter_instance.variable_name_to_value:
                self.inter_instance.variable_name_to_value[arg_name] = []
            #pass var by reference
            if arg.elem_type == 'refarg' and input_arg.elem_type == 'var':
                #if input variable does not exist, throw error
                if (input_arg.get('name') not in self.inter_instance.variable_name_to_value 
                    and input_arg.get('name') not in self.inter_instance.function_and_arg_counts):
                    self.inter_instance.throw_unknown_input_error(input_arg.get('name'))
                #if input variable is a variable in current scope
                elif input_arg.get('name') in self.inter_instance.variable_name_to_value:
                    ref_var, idx = self.inter_instance.get_referenced_variable(input_arg.get('name'))
                    #if trying to reference a variable that is not a reference
                    if idx == -1:
                        idx = len(self.inter_instance.variable_name_to_value[input_arg.get('name')]) - 1
                    #(idx of place in variable stack that is referred to, referred variable)
                    self.inter_instance.variable_name_to_value[arg_name].append((idx, ref_var))
                #if input variable is the name of a function
                else:
                    #assign corresponding function object to formal parameter
                    self.inter_instance.variable_name_to_value[arg_name].append(self.inter_instance.evaluate_variable(input_arg))
            else:
            #add input value as new value in the stack corresponding to variable name
                input_arg_value = self.inter_instance.evaluate_expression(input_args[i])
                self.inter_instance.variable_name_to_value[arg_name].append(input_arg_value)

        #add previously captured variables to current scope
        for closure_var_name, closure_var_value in self.closure_vars.items():
            #if closure variable hasn't been shadowed by arg
            if closure_var_name not in self.arg_names:
                local_vars.add(closure_var_name)

                #add closure variable to dict of all variables currently in-scope
                if closure_var_name not in self.inter_instance.variable_name_to_value:
                    self.inter_instance.variable_name_to_value[closure_var_name] = []
                self.inter_instance.variable_name_to_value[closure_var_name].append(closure_var_value)
                
        for statement in self.statements:
            #check if statement is assignment
            if statement.elem_type == '=':
                var_name = statement.get('name')
                if var_name not in self.inter_instance.variable_name_to_value:
                    local_vars.add(var_name)
                self.inter_instance.run_statement(statement)
            else:
                self.inter_instance.run_statement(statement)
                if self.inter_instance.is_returning:
                    #update closure var list so that if lambda is called again the updated values stay
                    self.update_closure_vars()
                    #clean scope because returning from function
                    self.inter_instance.clean_scope(local_vars)
                    self.inter_instance.is_returning = False #set to false because we stop
                        #returning once we return out of a function
                    return self.inter_instance.return_value

        self.update_closure_vars()
        self.inter_instance.clean_scope(local_vars) 
        self.inter_instance.is_returning = False
        #return nil if no return statement in function
        return None  
    
    #update closure variables before returning to maintain new values for next lambda call
    def update_closure_vars(self):
        for closure_var_name in self.closure_vars:
            #if closure var wasn't shadowed by formal parameter
            if closure_var_name not in self.arg_names:
                #if closure var is reference
                if type(self.inter_instance.variable_name_to_value[closure_var_name][-1]) is tuple:
                    ref_var = self.inter_instance.variable_name_to_value[closure_var_name][-1][1]
                    idx = self.inter_instance.variable_name_to_value[closure_var_name][-1][0]
                    value = self.inter_instance.variable_name_to_value[ref_var][idx]
                else:
                    value =  self.inter_instance.variable_name_to_value[closure_var_name][-1]
                self.closure_vars[closure_var_name] = value

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
    
    def run(self, program):
        ast = parse_program(program)         # parse program into AST
        self.variable_name_to_value = {}  # dict to hold var name as key and stack for values
        self.function_and_arg_counts = defaultdict(dict) # dict of dicts to hold each function, 
                                    #and nested dicts for arg counts (for overloading)
        self.is_returning = False #return flag set to true if current returning out of blocks
        self.return_value = None #return value

        main_func = self.evaluate_func_definitions(ast)
       
        #if there exists a main function
        if main_func:
            self.run_function(main_func, [])
        else: #throw error since no main
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )

    def throw_unknown_lambda_error(self, num_args):
        super().error(ErrorType.TYPE_ERROR,
                f"Unknown lambda with with arg length {num_args}")
        
    def throw_unknown_input_error(self, arg_name):
        super().error(ErrorType.NAME_ERROR,
                        f"Variable {arg_name} has not been defined",)
        
    #returns var_name if var isn't a reference, otherwise returns
    #referenced variable and idx of its stack that contains referenced value
    def get_referenced_variable(self, var_name):
        if type(self.variable_name_to_value[var_name][-1]) is tuple:
            ref_var = self.variable_name_to_value[var_name][-1][1]
            idx = self.variable_name_to_value[var_name][-1][0]
            return ref_var, idx
        else:
            return var_name, -1
        
    #iterate through all func definition nodes and store Function objects into function_and_arg_counts
    #return main Function object if it exists
    def evaluate_func_definitions(self, ast):
        functions = ast.get("functions")
        main_func = None
        for func in functions:
            name = func.get("name")
            num_args = len(func.get("args"))
            self.function_and_arg_counts[name][num_args] = Function(func)
            if name == "main":
                main_func = self.function_and_arg_counts[name][num_args]

        return main_func

    #run statement nodes (either assignment, function call, if, while, or return)
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
            return_value = self.evaluate_return_statement(statement_node)
            self.is_returning = True #set to true since we are returning
            self.return_value = return_value #store value to be returned

    def do_assignment(self, statement_node):
        target_var_name = statement_node.get("name")
        source_node = statement_node.get("expression")
        resulting_value = self.evaluate_expression(source_node)

        #if variable hasn't been created before or has gone out of scope
        if (target_var_name not in self.variable_name_to_value or 
                len(self.variable_name_to_value[target_var_name]) == 0):
            self.variable_name_to_value[target_var_name] = [resulting_value]
        #if variable exists, reassign existing local var (top of stack)
        elif len(self.variable_name_to_value[target_var_name]) > 0:
            ref_var, idx = self.get_referenced_variable(target_var_name)
            self.variable_name_to_value[ref_var][idx] = resulting_value

    #takes in list of local vars and pops the last value assigned to each variable
    def clean_scope(self, local_vars):
        for local_var in local_vars:
            self.variable_name_to_value[local_var].pop()
            #if variable has no assigned value, delete it
            if len(self.variable_name_to_value[local_var]) == 0:
                del self.variable_name_to_value[local_var]

    def evaluate_if_statement(self, if_node):
        local_vars = set() #stores variables that will go out of scope when if statement ends
        condition = if_node.get('condition')
        true_statements = if_node.get('statements')
        false_statements = if_node.get('else_statements')
        result = self.evaluate_expression(condition)
      
        #check if result is boolean
        if not isinstance(result, int):
            super().error(ErrorType.TYPE_ERROR,
                        f"condition does not evaluate to boolean")
        if result:
            for statement in true_statements:
                #if statement is assignment
                if statement.elem_type == '=':
                    var_name = statement.get('name')
                    #if variable hasn't been created in scope yet, add to local_vars
                    if (var_name not in self.variable_name_to_value or 
                        len(self.variable_name_to_value[var_name]) == 0):
                        local_vars.add(var_name)
                    self.run_statement(statement)
                else:
                    self.run_statement(statement)
                    #if we are returning
                    if self.is_returning:
                        self.clean_scope(local_vars)
                        return self.return_value
        else:
            if false_statements is None:
                return
            for statement in false_statements:
                #check if statement is assignment
                if statement.elem_type == '=':
                    var_name = statement.get('name')
                    if (var_name not in self.variable_name_to_value or 
                        len(self.variable_name_to_value[var_name]) == 0):
                        local_vars.add(var_name)
                    self.run_statement(statement)
                else:
                    self.run_statement(statement)
                    if self.is_returning:
                        self.clean_scope(local_vars)
                        return self.return_value
        #clean scope since we are returning
        self.clean_scope(local_vars)

    def evaluate_while_statement(self, while_node):
        local_vars = set() 
        condition = while_node.get('condition')
        statements = while_node.get('statements')

        #check if condition is boolean expression
        if not isinstance(self.evaluate_expression(condition), int):
            super().error(ErrorType.TYPE_ERROR,
                        f"condition does not evaluate to boolean")
            
        while(self.evaluate_expression(condition)):
            for statement in statements:
                #check if statement is assignment
                if statement.elem_type == '=':
                    var_name = statement.get('name')
                    if (var_name not in self.variable_name_to_value or 
                        len(self.variable_name_to_value[var_name]) == 0):
                        local_vars.add(var_name)
                    self.run_statement(statement)
                else:
                    self.run_statement(statement)
                    if self.is_returning:
                        self.clean_scope(local_vars)
                        return self.return_value
                    
            #continue checking if condition is boolean
            if not isinstance(self.evaluate_expression(condition), int):
                super().error(ErrorType.TYPE_ERROR,
                            f"condition does not evaluate to boolean")
        self.clean_scope(local_vars)

    def evaluate_return_statement(self, return_node):
        expression = return_node.get('expression')
        if expression is None:
            return None
        evaluated_expression = self.evaluate_expression(expression)
      
        #if expression is function, return deep copy
        if isinstance(evaluated_expression, Function):
            return Function(evaluated_expression.function_node)
        #if expression is lambda, return deep copy
        elif isinstance(evaluated_expression, Lambda):
            return Lambda(evaluated_expression.lambda_node, copy.deepcopy(evaluated_expression.closure_vars), self)

        return evaluated_expression
    
    def evaluate_expression(self, expression_node):
        #if expression is function call
        if expression_node.elem_type == 'fcall':
            return self.do_func_call(expression_node)
        #if expression is unary operator
        elif expression_node.elem_type == 'neg' or expression_node.elem_type == '!':
            return self.evaluate_unary_op(expression_node)
        #if expression is variable
        elif expression_node.elem_type == 'var':
            return self.evaluate_variable(expression_node)
        #if expression is value
        elif (expression_node.elem_type == 'int' or expression_node.elem_type == 'string' or
            expression_node.elem_type == 'bool' or expression_node.elem_type == 'nil'):
            return self.evaluate_value(expression_node)
        #if expression is lambda expression
        elif expression_node.elem_type == 'lambda':
            return self.evaluate_lambda(expression_node)
        #if expression is binary operator
        else:
            return self.evaluate_binary_operator(expression_node)

    def evaluate_binary_operator(self, binary_expression):
        op1 = binary_expression.get('op1')
        op2 = binary_expression.get('op2')
        
        #evaluate opt1
        op1_value = self.evaluate_expression(op1)
        #evaluate op2
        op2_value = self.evaluate_expression(op2)
 
        op = binary_expression.elem_type

        #throw error if operands are different types and op is not '==' or '!='
        if (type(op1_value) != type(op2_value) and op != '==' and op != '!=' and  
            not isinstance(op1_value, int) and not isinstance(op2_value, int)):
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for operation",
            )

        match op:
            case '+':
                #'+' only works on ints and strings
                if (op1_value is not None and not isinstance(op1_value, Function)
                    and not isinstance(op1_value, Lambda)):
                    return op1_value + op2_value
            case '-':
                #'-' only works in ints
                if isinstance(op1_value, int):
                    return op1_value - op2_value
            case '*':
                #'*' only works in ints
                if isinstance(op1_value, int):
                    return op1_value * op2_value
            case '/':
                #'/' only works in ints
                if isinstance(op1_value, int):
                    return op1_value // op2_value
            case '==':
                #'==' returns false if different types
                if (type(op1_value) != type(op2_value) and not isinstance(op1_value, int) 
                    and not isinstance(op2_value, int)):
                    return False
                #int is false if it is 0, otherwise true
                if(isinstance(op1_value, int) and isinstance(op2_value, bool)):
                    op1_value = False if (op1_value == 0) else True 
                if(isinstance(op2_value, int) and isinstance(op1_value, bool)):
                    op2_value = False if (op2_value == 0) else True 
                return op1_value == op2_value
            case '!=':
                #'!=' returns true if different types
                if (type(op1_value) != type(op2_value) and not isinstance(op1_value, int) 
                    and not isinstance(op2_value, int)):
                    return True
                #int is false if it is 0, otherwise true
                if(isinstance(op1_value, int) and isinstance(op2_value, bool)):
                    op1_value = False if (op1_value == 0) else True 
                if(isinstance(op2_value, int) and isinstance(op1_value, bool)):
                    op2_value = False if (op2_value == 0) else True 
                return op1_value != op2_value
            case '<':
                #'<' only works in ints
                if not isinstance(op1_value, bool) and not isinstance(op2_value, bool) and isinstance(op1_value, int):
                    return op1_value < op2_value
            case '<=':
                #'<=' only works in ints
                if not isinstance(op1_value, bool) and not isinstance(op2_value, bool) and isinstance(op1_value, int):
                    return op1_value <= op2_value
            case '>':
                #'>' only works in ints
                if not isinstance(op1_value, bool) and not isinstance(op2_value, bool) and isinstance(op1_value, int):
                    return op1_value > op2_value
            case '>=':
                #'>=' only works in ints
                if not isinstance(op1_value, bool) and not isinstance(op2_value, bool) and isinstance(op1_value, int):
                    return op1_value >= op2_value
            case '||':
                #int is false if it is 0, true otherwise
                if(isinstance(op1_value, int)):
                    op1_value = False if (op1_value == 0) else True 
                if(isinstance(op2_value, int)):
                    op2_value = False if (op2_value == 0) else True 
                if isinstance(op1_value, bool):
                    return op1_value or op2_value
            case '&&':
                #int is false if it is 0, true otherwise
                if(isinstance(op1_value, int)):
                    op1_value = False if (op1_value == 0) else True 
                if(isinstance(op2_value, int)):
                    op2_value = False if (op2_value == 0) else True 
                if isinstance(op1_value, bool):
                    return op1_value and op2_value

        #throw error because wrong types
        super().error(
            ErrorType.TYPE_ERROR,
            "Incompatible types for operation",
        )

    def evaluate_unary_op(self, unary_node):
        op1 = unary_node.get('op1')
        op1_value = self.evaluate_expression(op1)
            
        if unary_node.elem_type == '!' and isinstance(op1_value, int):
            return not op1_value
        elif unary_node.elem_type == 'neg' and isinstance(op1_value, int) and not isinstance(op1_value, bool):
            return -1*op1_value
        
        #wrong types for unary op
        super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for unary operation",
            )

    #creates Lambda object that captures current scope
    def evaluate_lambda(self, lambda_node):
        current_scope = {}
        for var, value in self.variable_name_to_value.items():
            ref_var, idx = self.get_referenced_variable(var)
            value = self.variable_name_to_value[ref_var][idx]
            current_scope[var] = value

        new_lambda = Lambda(lambda_node, copy.deepcopy(current_scope), self)

        return new_lambda

    def evaluate_variable(self, variable_node):
        var_name = variable_node.get('name')
        #if variable exists in dictionary with a stack of at least size 1
        if (var_name in self.variable_name_to_value and 
                len(self.variable_name_to_value[var_name]) > 0):
            ref_var, idx = self.get_referenced_variable(var_name)
            return self.variable_name_to_value[ref_var][idx]
        #if variable exists as a function name
        elif var_name in self.function_and_arg_counts:
            #if function is an overloaded function, throw error
            if len(self.function_and_arg_counts[var_name]) > 1:
                super().error(ErrorType.NAME_ERROR,
                        f"Cannot use overloaded function as a variable",)
            #return Function object corresponding to variable name
            else:
                return list(self.function_and_arg_counts[var_name].values())[0]
        else:
            super().error(ErrorType.NAME_ERROR,
                        f"Variable {var_name} has not been defined",)
    
    def evaluate_value(self, value_node):
        return value_node.get('val')

    def do_func_call(self, func_node):
        func_to_be_called = func_node.get('name')
        args = func_node.get('args')

        #print function
        if func_to_be_called == 'print':
            self.do_print(args)
            return None
        #inputi fuction
        elif func_to_be_called == 'inputi':
            return self.do_inputi(args)
        #inputs function
        elif func_to_be_called == 'inputs':
            return self.do_input(args)
        #if function exists in function dict
        elif func_to_be_called in self.function_and_arg_counts:
            #if function exists with same num of args
            if len(args) in self.function_and_arg_counts[func_to_be_called]:
                return self.run_function(self.function_and_arg_counts[func_to_be_called][len(args)], args)
        #if it's a variable that stores a lambda or first-class function
        elif func_to_be_called in self.variable_name_to_value:
            ref_var, idx = self.get_referenced_variable(func_to_be_called)
            var_value = self.variable_name_to_value[ref_var][idx]
            #throw type error if trying to call function through a variable that doesn't hold function
            if not isinstance(var_value, Function) and not isinstance(var_value, Lambda):
                super().error(ErrorType.TYPE_ERROR,
                    f"Variable does not store function or lambda")
            elif isinstance(var_value, Function):
                #run function if number of inputs matches number of args
                if len(args) == var_value.num_args:
                    return self.run_function(var_value, args)
                else:
                    super().error(ErrorType.TYPE_ERROR,
                    f"Unknown function {func_to_be_called} with arg length {len(args)}")
            elif isinstance(var_value, Lambda):
                    #run lambda function
                    return var_value.run_lambda(args)
        #unknown function
        super().error(ErrorType.NAME_ERROR,
                    f"Unknown function {func_to_be_called} with arg length {len(args)}")
    
    def run_function(self, func_obj, input_args):
        func_node = func_obj.function_node
        local_vars = set() #local to function (not including inner blocks or func calls)
        func_args = func_node.get('args')
        func_statements = func_node.get('statements')

        for i in range(len(func_args)):
            arg = func_args[i]
            arg_name = arg.get('name')
            input_arg = input_args[i]
            local_vars.add(arg_name) #add arg as local variable
            #if arg variable has not been created before in dict
            if arg_name not in self.variable_name_to_value:
                self.variable_name_to_value[arg_name] = []
            #pass var by reference
            if arg.elem_type == 'refarg' and input_arg.elem_type == 'var':
                #throw error if input is not defined
                if (input_arg.get('name') not in self.variable_name_to_value 
                    and input_arg.get('name') not in self.function_and_arg_counts):
                    super().error(ErrorType.NAME_ERROR,
                        f"Variable {input_arg.get('name')} has not been defined",)
                #if input is a variable
                elif input_arg.get('name') in self.variable_name_to_value:
                    ref_var, idx = self.get_referenced_variable(input_arg.get('name'))
                    #if trying to reference a variable that is not a reference
                    if idx == -1:
                        idx = len(self.variable_name_to_value[input_arg.get('name')]) - 1
                    #(idx of place in variable stack that is referred to, referred variable)
                    self.variable_name_to_value[arg_name].append((idx, ref_var))
                #if input is a function name
                else:
                    self.variable_name_to_value[arg_name].append(self.evaluate_variable(input_arg))
            else:
            #add input value as new value in the stack corresponding to variable name
                input_arg_value = self.evaluate_expression(input_args[i])
                #if a Lambda is passed in by value, make a copy of it
                if(isinstance(input_arg_value, Lambda)):
                    input_arg_value = Lambda(input_arg_value.lambda_node, copy.deepcopy(input_arg_value.closure_vars), self)
                self.variable_name_to_value[arg_name].append(input_arg_value)

        for statement in func_statements:
            #check if statement is assignment
            if statement.elem_type == '=':
                var_name = statement.get('name')
                if (var_name not in self.variable_name_to_value or 
                    len(self.variable_name_to_value[var_name]) == 0):
                    local_vars.add(var_name)
                self.run_statement(statement)
            else:
                self.run_statement(statement)
                if self.is_returning:
                    #clean scope because returning from function
                    self.clean_scope(local_vars)
                    self.is_returning = False #set to false because we stop
                        #returning once we return out of a function
                    return self.return_value

        self.clean_scope(local_vars) 
        self.is_returning = False
        #return nil if no return statement in function
        return None       

    def do_print(self, args):
        print_string = ""
        #concatenate each argument for print() to output string
        for arg in args:
            arg_val = self.evaluate_expression(arg)
            arg_val_print = "" #string form of arg to be printed
            #if value is of type bool, convert to corresponding strings
            if isinstance(arg_val, bool):
                if arg_val:
                    arg_val_print = "true"
                else:
                    arg_val_print = "false"
            else:
                arg_val_print = str(arg_val)
            print_string = print_string + arg_val_print
            
        super().output(print_string)
        return None

    def do_inputi(self, args):
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
    
    def do_input(self, args):
        #if length of arg > 1, throw error
        if len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR,
                f"No input() function found that takes > 1 parameter",
            )
            
        #print prompt if there is one
        if len(args) == 1:
            prompt = args[0]
            super().output(self.evaluate_value(prompt))
        
        user_input = super().get_input()
        return str(user_input)

def main():
    interpreter = Interpreter()
    program1 = """func foo(f1, ref f2) {
  f1(); /* prints 1 */
  f2(); /* prints 1 */
}

func main() {
    print(-1 == false);
  x = 0;
  lam1 = lambda() { x = x + 1; print(x); };
  lam2 = lambda() { x = x + 1; print(x); };
  foo(lam1, lam2);
  lam1(); /* prints 1 */
  lam2(); /* prints 2 */
}
    """
    interpreter.run(program1)

if __name__ == "__main__":
    main()