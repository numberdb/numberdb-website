
from services.eval import SafeEval

SE = SafeEval()
programs = []
programs.append('[n for n in range(Integer(10))]')

for program in programs:
    print('--------')
    print('program:',program)
    result = SE.eval_search_program(program)
    param_numbers, messages_eval = loads(bytes(result, encoding='cp437'))
    print('param_numbers:',param_numbers)
    print('messages_eval:',messages_eval)
