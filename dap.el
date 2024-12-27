;; Eval Buffer with `M-x eval-buffer' to register the newly created template.

(dap-register-debug-template
 "LISP code-gen"
 (list :name "LISP code-gen"
       :type "python"
       :args (list
              "--extension" "cmd"
              "--language" "lisp"
              "--export-path" "C:/workspace/lisp/komorebi/komorebi-api.el"
              "--emacs"
              )
       :cwd "c:/workspace/python/private/pyKomorebi"
       :module "code_gen"
       :program nil
       :request "launch"))
