import traceback

class DeliveryMatchException(Exception):
    pass
#     def __init__(self, message,  input=None, output=None):
#         super().__init__(message)
#         tb = traceback.format_exc()

#         self.step = f"step: {traceback.extract_tb(tb)[-1][1]}"
#         self.error = f"error: {traceback.extract_tb(tb)[-1][2]}"
#         self.input = input
#         self.output = output
    
#     def error_location(self):
#         return f"""{self.step}
# {self.error}"""