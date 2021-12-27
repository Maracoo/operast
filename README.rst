Operast
=======

Design Goal: To cleanly separate the logic for ast navigation from the logic
applied by the visitor to a visited node.


When trying to find a function with a specific name it is not possible to alter
the name of that function dynamically and search for the resulting parsed
function def, as parsing the function will result in the structure defined
*before* any dynamic occurrence has taken place.
