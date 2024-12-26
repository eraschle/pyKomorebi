;; Eval Buffer with `M-x eval-buffer' to register the newly created template.

(dap-register-debug-template
 "LISP code-gen"
 (list :name "LISP gen"
       :type "python"
       :args '("--import-path" "C:\\workspace\\komorebi\\docs\\cli\\"
               "--extension" "cmd"
               "--language" "lisp"
               "--export-path" "C:\\workspace\\lisp\\komorebi\\komorebi-api.el"
               )
       :cwd "c:\\workspace\\python\\private\\pyKomorebi\\"
       :module "code_gen"
       :program nil
       :request "launch"))
