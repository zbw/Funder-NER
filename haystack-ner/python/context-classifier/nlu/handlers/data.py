from nlu import utils
from nlu.expression import Expression


def load_training_data(filepath):
    '''
    loads training data from local file (set in config) and extract expressions
    returns (dict of array of expressions)
    '''
    print('loading training data from {}'.format(filepath))
    training_data = utils.json_load(filepath)
    expressions = load_expressions(training_data)
    return expressions


def load_expressions(training_data):
    '''
    loads expressions for training from training file and creates
    expression instance for every expression.
    returns array of expression-instances
    '''
    print('loading expressions from training data')

    expressions = training_data.get('expressions')

    assert expressions is not None, (
           'data-handler: load_train_expressions: '
           'no expressions found in document')

    assert type(expressions) is list, (
           'data-handler: load_train_expressions: '
           'expressions must be a list')

    valid_exps = []
    for exp in expressions:
        text = exp.get('text')
        intent = exp.get('intent')
        valid_exp = Expression(text, intent)
        valid_exps.append(valid_exp)

    print('successfully loaded {} expressions'.format(len(valid_exps)))
    return valid_exps
