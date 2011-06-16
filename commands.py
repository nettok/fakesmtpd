import json

from collections import namedtuple

from mail_hooks import AddressFilter


address_filter = AddressFilter()


# /==================================== EXCEPTIONS ===============================================\

class EndOfRoute(ValueError):
    pass

class RouteAlreadyExists(ValueError):
    pass
    
# \===============================================================================================/


# /==================================== COMMANDS =================================================\

def quit(subscriber):
    subscriber.unsubscribe()

def filter_enable(subscriber):
    if not subscriber.mail_hook_exists(address_filter):
        subscriber.add_mail_hook(address_filter)
        return 'filter enabled'
    else:
        return 'filter already enabled'
        
def filter_disable(subscriber):
    if subscriber.remove_mail_hook(address_filter):
        return 'filter disabled'
    else:
        return 'filter already disabled'
        
def filter_state(subscriber):
    resp = ""
    
    if subscriber.mail_hook_exists(address_filter):
        resp += 'filter enabled\n\n'
    else:
        resp += 'filter disabled\n\n'
        
    resp += json.dumps(address_filter.get_state(), indent=4)
        
    return resp

def filter_reset(subscriber):
    address_filter.reset()
    return 'Ok'
    
def filter_clear(subscriber, ctx, filter_name):
    try:
        address_filter.clear(ctx, filter_name)
        return 'Ok'
    except ValueError as e:
        return str(e)
    
def filter_use(subscriber, ctx, filter_name):
    try:
        address_filter.use(ctx, filter_name)
        return 'Ok'
    except ValueError as e:
        return str(e)
    
def filter_update(subscriber, ctx, filter_name, *addresses):
    try:
        address_filter.update(ctx, filter_name, addresses)
        return 'Ok'
    except ValueError as e:
        return str(e)

# \===============================================================================================/

    
class CommandTree(object):
    Node = namedtuple('Node', ['name', 'func', 'children'])
    
    def __init__(self):
        self._root = CommandTree.Node('root', None, [])
    
    def create_route(self, route, func):
        current_node = self._root
        route_len = len(route)
        
        assert callable(func)
        assert route_len > 0
        
        for n, node_name in enumerate(route, start=1):
            for child in current_node.children:
                if (child.name == node_name):
                    # walk route
                    if (n == route_len):
                        raise RouteAlreadyExists()
                    elif callable(child.func):
                        raise EndOfRoute(node_name)
                    current_node = child
                    break
            else:
                # build route
                if n == route_len:
                    f = func
                else:
                    f = None
                new_child = CommandTree.Node(node_name, f, [])
                current_node.children.append(new_child)
                current_node = new_child
                
    def execute_route(self, subscriber, route):
        current_node = self._root
        route_len = len(route)
        
        assert route_len > 0
        
        for n, node_name in enumerate(route, start=1):
            for child in current_node.children:
                if (child.name == node_name):
                    # walk route
                    if callable(child.func):
                        # route found
                        try:
                            return child.func(subscriber, *route[n:])
                        except TypeError:
                            return 'Error al ejecutar el comando, revise los argumentos'
                    current_node = child
                    break

        # route does not exist
        return 'Linea de comando invalida'
        
        
command_tree = CommandTree()
command_tree.create_route(['quit'], quit)
command_tree.create_route(['filter', 'enable'], filter_enable)
command_tree.create_route(['filter', 'disable'], filter_disable)
command_tree.create_route(['filter', 'state'], filter_state)
command_tree.create_route(['filter', 'reset'], filter_reset)
command_tree.create_route(['filter', 'clear'], filter_clear)
command_tree.create_route(['filter', 'use'], filter_use)
command_tree.create_route(['filter', 'update'], filter_update)


def run_command(subscriber, input_line):
    input_ = input_line.strip().split()
    
    if len(input_) == 0:
        return
        
    resp = command_tree.execute_route(subscriber, input_)
    
    if resp is not None:
        subscriber.send(resp.replace('\n', '\n\r')+'\n\n\r', False)
