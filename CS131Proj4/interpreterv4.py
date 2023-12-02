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
                    ref_var, idx = self.inter_instance.get_referenced_variable(self.inter_instance.variable_name_to_value, input_arg.get('name'))
                    #if trying to reference a variable that is not a reference
                    if idx == -1:
                        idx = len(self.inter_instance.variable_name_to_value[input_arg.get('name')]) - 1
                    #(idx of place in variable stack that is referred to, referred variable)
                    self.inter_instance.variable_name_to_value[arg_name].append((idx, ref_var))
                #if input variable is the name of a function
                else:
                    #assign corresponding function object to formal parameter
                    self.inter_instance.variable_name_to_value[arg_name].append(self.inter_instance.evaluate_variable(self.inter_instance.variable_name_to_value, input_arg))
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
                if var_name not in self.inter_instance.variable_name_to_value and '.' not in var_name and var_name != 'this':
                    local_vars.add(var_name)
                self.inter_instance.run_statement(statement)
            else:
                self.inter_instance.run_statement(statement)
                if self.inter_instance.is_returning:
                    #update closure var list so that if lambda is called again the updated values stay
                    self.update_closure_vars()
                    #clean scope because returning from function
                    self.inter_instance.clean_scope(self.inter_instance.variable_name_to_value, local_vars)
                    self.inter_instance.is_returning = False #set to false because we stop
                        #returning once we return out of a function
                    return self.inter_instance.return_value

        self.update_closure_vars()
        self.inter_instance.clean_scope(self.inter_instance.variable_name_to_value, local_vars) 
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
                    ref_var, idx = self.inter_instance.get_referenced_variable(self.inter_instance.variable_name_to_value, closure_var_name)
                    value = self.inter_instance.variable_name_to_value[ref_var][idx]
                else:
                    value = self.inter_instance.variable_name_to_value[closure_var_name][-1]
                self.closure_vars[closure_var_name] = value

class Object(InterpreterBase):
    def __init__(self, interpreter_instance, fields=None, parent=None):
        if fields is None:
            self.fields = {}
        else:
            self.fields = fields
        self.parent = parent
        self.inter_instance = interpreter_instance
        #print("init " + str(self))

    def get_field(self, field_name):
        #print(str(self))
        #if getting proto
        if field_name == 'proto':
            #if no proto, throw error
            if self.parent == None:
                self.inter_instance.throw_unknown_field_error(field_name)
            return self.parent
        #if field doesn't exist, throw error
        curr_obj = self
        while field_name not in curr_obj.fields:
            curr_obj = curr_obj.parent
            if curr_obj == None:
                self.inter_instance.throw_unknown_field_error(field_name)
            
        return curr_obj.fields[field_name][-1]
    
    def assign_field(self, field_name, value):
        #print(str(self))
        #if assigning prototype
        if field_name == 'proto':
            #throw error if value is not of type object
            if not isinstance(value, Object) and value != None:
                self.inter_instance.throw_invalid_prototype_error()
            self.parent = value
        else:
            self.inter_instance.do_assignment(self.fields, field_name, value)

    def __str__(self):
        return "fields " + str(self.fields) + " parent " + str(self.parent)
        
            
        
    
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
        self.child_object = [] #current object scope if we're in a method
        self.inside_method = False #set to true when a method is called

        main_func = self.evaluate_func_definitions(ast)

        #print(ast)
       
        #if there exists a main function
        if main_func:
            self.run_function(self.variable_name_to_value, main_func, [])
        else: #throw error since no main
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )

    def throw_unknown_lambda_error(self, num_args):
        super().error(ErrorType.NAME_ERROR,
                f"Unknown lambda with with arg length {num_args}")
        
    def throw_unknown_input_error(self, arg_name):
        super().error(ErrorType.NAME_ERROR,
                        f"Variable {arg_name} has not been defined",)
        
    def throw_unknown_field_error(self, field_name):
        super().error(ErrorType.NAME_ERROR,
                        f"Field {field_name} not found")
        
    def throw_invalid_prototype_error(self):
        super().error(ErrorType.TYPE_ERROR,
                    f"Assigning invalid type as prototype")
        
    #returns var_name if var isn't a reference, otherwise returns
    #referenced variable and idx of its stack that contains referenced value
    def get_referenced_variable(self, scope_var_list, var_name):
        if type(scope_var_list[var_name][-1]) is tuple:
            ref_var = scope_var_list[var_name][-1][1]
            idx = scope_var_list[var_name][-1][0]
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
        #print(str(self.variable_name_to_value))
        if statement_node.elem_type == '=':
            target_var_name, resulting_value = self.evaluate_assignment_node(statement_node)
            self.do_assignment(self.variable_name_to_value, target_var_name, resulting_value)
        elif statement_node.elem_type == 'fcall':
            self.do_func_call(self.variable_name_to_value, statement_node)
        #if expression is method call
        elif statement_node.elem_type == 'mcall':
            self.evaluate_method_call(self.variable_name_to_value, statement_node)
        elif statement_node.elem_type == 'if':
            self.evaluate_if_statement(self.variable_name_to_value, statement_node)
        elif statement_node.elem_type == 'while':
            self.evaluate_while_statement(self.variable_name_to_value, statement_node)
        elif statement_node.elem_type == 'return':
            return_value = self.evaluate_return_statement(statement_node)
            self.is_returning = True #set to true since we are returning
            self.return_value = return_value #store value to be returned

    def evaluate_assignment_node(self, statement_node):
        target_var_name = statement_node.get("name")
        source_node = statement_node.get("expression")
        resulting_value = self.evaluate_expression(source_node)
        return target_var_name, resulting_value

    def do_assignment(self, scope_var_list, target_var_name, resulting_value):
        #if variable is accesssing field of object
        if '.' in target_var_name:
            object_name = target_var_name[0:target_var_name.index('.')]
            field_name = target_var_name[target_var_name.index('.') + 1:]
            
            object = self.get_object(object_name)
                
            object.assign_field(field_name, resulting_value)
        #if variable is 'this'
        elif target_var_name == "this":
            ref_var, idx = self.get_referenced_variable(scope_var_list, self.child_object[-1][0])
            #throw error if resulting value is not an object
            # if not isinstance(resulting_value, Object) and resulting_value != None:
            #     super().error(ErrorType.TYPE_ERROR,
            #             f"Cannot assign non-object to 'this'")
            self.child_object[-1] = (self.child_object[-1][0], resulting_value)
            scope_var_list[ref_var][idx] = resulting_value
        #if variable hasn't been created before or has gone out of scope
        elif (target_var_name not in scope_var_list or 
                len(scope_var_list[target_var_name]) == 0):
            scope_var_list[target_var_name] = [resulting_value]
        #if variable exists, reassign existing local var (top of stack)
        elif len(scope_var_list[target_var_name]) > 0:
            ref_var, idx = self.get_referenced_variable(scope_var_list, target_var_name)
            scope_var_list[ref_var][idx] = resulting_value

    #takes in list of local vars and pops the last value assigned to each variable
    def clean_scope(self, scope_var_list, local_vars):
        for local_var in local_vars:
            scope_var_list[local_var].pop()
            #if variable has no assigned value, delete it
            if len(scope_var_list[local_var]) == 0:
                del scope_var_list[local_var]

    def evaluate_if_statement(self, scope_var_list, if_node):
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
                    #if variable hasn't been created in scope yet, add to local_vars and variable is not a field
                    if var_name not in scope_var_list and '.' not in var_name and var_name != 'this':
                        local_vars.add(var_name)
                    self.run_statement(statement)
                else:
                    self.run_statement(statement)
                    #if we are returning
                    if self.is_returning:
                        self.clean_scope(self.variable_name_to_value, local_vars)
                        return self.return_value
        else:
            if false_statements is None:
                return
            for statement in false_statements:
                #check if statement is assignment
                if statement.elem_type == '=':
                    var_name = statement.get('name')
                    if var_name not in scope_var_list and '.' not in var_name and var_name != 'this':
                        local_vars.add(var_name)
                    self.run_statement(statement)
                else:
                    self.run_statement(statement)
                    if self.is_returning:
                        self.clean_scope(self.variable_name_to_value, local_vars)
                        return self.return_value
        #clean scope since we are returning
        self.clean_scope(self.variable_name_to_value, local_vars)

    def evaluate_while_statement(self, scope_var_list, while_node):
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
                    if var_name not in scope_var_list and '.' not in var_name and var_name != 'this':
                        local_vars.add(var_name)
                    self.run_statement(statement)
                else:
                    self.run_statement(statement)
                    if self.is_returning:
                        self.clean_scope(self.variable_name_to_value, local_vars)
                        return self.return_value
                    
            #continue checking if condition is boolean
            if not isinstance(self.evaluate_expression(condition), int):
                super().error(ErrorType.TYPE_ERROR,
                            f"condition does not evaluate to boolean")
        self.clean_scope(self.variable_name_to_value, local_vars)

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
        elif isinstance(evaluated_expression, Object):
            return copy.deepcopy(evaluated_expression)

        return evaluated_expression
    
    def evaluate_expression(self, expression_node):
        #if expression is function call
        if expression_node.elem_type == 'fcall':
            return self.do_func_call(self.variable_name_to_value, expression_node)
        #if expression is unary operator
        elif expression_node.elem_type == 'neg' or expression_node.elem_type == '!':
            return self.evaluate_unary_op(expression_node)
        #if expression is variable
        elif expression_node.elem_type == 'var':
            return self.evaluate_variable(self.variable_name_to_value, expression_node)
        #if expression is value
        elif (expression_node.elem_type == 'int' or expression_node.elem_type == 'string' or
            expression_node.elem_type == 'bool' or expression_node.elem_type == 'nil'):
            return self.evaluate_value(expression_node)
        #if expression is lambda expression
        elif expression_node.elem_type == 'lambda':
            return self.evaluate_lambda(self.variable_name_to_value, expression_node)
        #if expression is method call
        elif expression_node.elem_type == 'mcall':
            return self.evaluate_method_call(self.variable_name_to_value, expression_node)
        #if expression is object instantiation
        elif expression_node.elem_type == '@':
            return Object(self)
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
    def evaluate_lambda(self, scope_var_list, lambda_node):
        current_scope = {}
        for var, value in scope_var_list.items():
            ref_var, idx = self.get_referenced_variable(self.variable_name_to_value, var)
            value = scope_var_list[ref_var][idx]
            if not isinstance(value, Object) and not isinstance(value, Lambda):
                current_scope[var] = copy.deepcopy(value)
            else:
                if idx == -1:
                    current_scope[var] = (len(scope_var_list[ref_var]) - 1, ref_var)
                else:
                    current_scope[var] = (idx, ref_var)

        new_lambda = Lambda(lambda_node, current_scope, self)

        return new_lambda

    def evaluate_variable(self, scope_var_list, variable_node):
        var_name = variable_node.get('name')

        #if variable is accessing field of object
        if '.' in var_name:
            object_name = var_name[0:var_name.index('.')]
            field_name = var_name[var_name.index('.') + 1:]

            object = self.get_object(object_name)
                
            return object.get_field(field_name)
        
        #if variable exists in dictionary with a stack of at least size 1
        elif var_name in scope_var_list:
            ref_var, idx = self.get_referenced_variable(self.variable_name_to_value, var_name)
            return scope_var_list[ref_var][idx]
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
    
    def get_object(self, object_name):
        #if 'this' keyword is used
        if object_name == 'this':
            #if no object has been defined (aka we're not in a method), throw error
            if len(self.child_object) == 0:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Object 'this' not found",
                )
            #child_name, child_obj = self.child_object[-1]

            return self.child_object[-1][1]
        
        #if object has not been created, throw error
        if object_name not in self.variable_name_to_value:
            super().error(ErrorType.NAME_ERROR,
                f"Object {object_name} not found")
            
        ref_var, idx = self.get_referenced_variable(self.variable_name_to_value, object_name)
        #if object_name is not of type object
        if not isinstance(self.variable_name_to_value[ref_var][idx], Object):
            super().error(ErrorType.TYPE_ERROR,
                f"{object_name} is not an object")
            
        return self.variable_name_to_value[ref_var][idx]
            
    def evaluate_method_call(self, scope_var_list, method_node):
        object_name = method_node.get('objref')
        method_name = method_node.get('name')
        args = method_node.get('args')

        object = self.get_object(object_name)
        method = object.get_field(method_name)

        #if method_name is not of type lambda or function
        if not isinstance(method, Lambda) and not isinstance(method, Function):
            super().error(ErrorType.TYPE_ERROR,
                    f"{method_name} is not a method")
            
        self.child_object.append((object_name, object))

        #if method refers to a function
        if isinstance(method, Function):
            #run function if number of inputs matches number of args
            if len(args) == method.num_args:
                ans = self.run_function(self.variable_name_to_value, method, args)
            else:
                super().error(ErrorType.NAME_ERROR,
                f"Unknown function {method_name} with arg length {len(args)}")
        #if method is a closure
        elif isinstance(method, Lambda):
                #run lambda function
                ans = method.run_lambda(args)
        
        self.child_object.pop()
        return ans

    def do_func_call(self, scope_var_list, func_node):
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
                return self.run_function(self.variable_name_to_value, self.function_and_arg_counts[func_to_be_called][len(args)], args)
        #if it's a variable that stores a lambda or first-class function
        elif func_to_be_called in scope_var_list:
            ref_var, idx = self.get_referenced_variable(self.variable_name_to_value, func_to_be_called)
            var_value = scope_var_list[ref_var][idx]
            #throw type error if trying to call function through a variable that doesn't hold function
            if not isinstance(var_value, Function) and not isinstance(var_value, Lambda):
                super().error(ErrorType.TYPE_ERROR,
                    f"Variable does not store function or lambda")
            elif isinstance(var_value, Function):
                #run function if number of inputs matches number of args
                if len(args) == var_value.num_args:
                    return self.run_function(self.variable_name_to_value, var_value, args)
                else:
                    super().error(ErrorType.TYPE_ERROR,
                    f"Unknown function {func_to_be_called} with arg length {len(args)}")
            elif isinstance(var_value, Lambda):
                    #run lambda function
                    return var_value.run_lambda(args)
        #unknown function
        super().error(ErrorType.NAME_ERROR,
                    f"Unknown function {func_to_be_called} with arg length {len(args)}")
    
    def run_function(self, scope_var_list, func_obj, input_args):
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
            if arg_name not in scope_var_list:
                scope_var_list[arg_name] = []
            #pass var by reference
            if arg.elem_type == 'refarg' and input_arg.elem_type == 'var':
                #throw error if input is not defined
                if (input_arg.get('name') not in scope_var_list 
                    and input_arg.get('name') not in self.function_and_arg_counts):
                    super().error(ErrorType.NAME_ERROR,
                        f"Variable {input_arg.get('name')} has not been defined",)
                #if input is a variable
                elif input_arg.get('name') in scope_var_list:
                    ref_var, idx = self.get_referenced_variable(self.variable_name_to_value, input_arg.get('name'))
                    #if trying to reference a variable that is not a reference
                    if idx == -1:
                        idx = len(scope_var_list[input_arg.get('name')]) - 1
                    #(idx of place in variable stack that is referred to, referred variable)
                    scope_var_list[arg_name].append((idx, ref_var))
                #if input is a function name
                else:
                    scope_var_list[arg_name].append(self.evaluate_variable(self.variable_name_to_value, input_arg))
            else:
            #add input value as new value in the stack corresponding to variable name
                input_arg_value = self.evaluate_expression(input_args[i])
                #if a Lambda is passed in by value, make a copy of it
                if(isinstance(input_arg_value, Lambda)):
                    input_arg_value = Lambda(input_arg_value.lambda_node, copy.deepcopy(input_arg_value.closure_vars), self)
                if(isinstance(input_arg_value, Object)):
                    input_arg_value = copy.deepcopy(input_arg_value)
                scope_var_list[arg_name].append(input_arg_value)

        for statement in func_statements:
            #check if statement is assignment
            if statement.elem_type == '=':
                var_name = statement.get('name')
                if var_name not in scope_var_list and '.' not in var_name and var_name != 'this':
                    local_vars.add(var_name)
                self.run_statement(statement)
            else:
                self.run_statement(statement)
                if self.is_returning:
                    #clean scope because returning from function
                    self.clean_scope(self.variable_name_to_value, local_vars)
                    self.is_returning = False #set to false because we stop
                        #returning once we return out of a function
                    return self.return_value

        self.clean_scope(self.variable_name_to_value, local_vars) 
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
    program1 = """func foo(obj) {
    obj.y();
    obj.y();
}

func main() {
    x = @;
    z = 0;
    x.y = lambda() {z = z + 1; print(z);};
    foo(x);
    x.y();
}
    """
    interpreter.run(program1)

if __name__ == "__main__":
    main()