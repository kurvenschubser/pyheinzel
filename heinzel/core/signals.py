from weakref import ref


SIGNALS = {
	# Add your own signal definition like this:
	# signalname: (required_arg_1, required_arg_2, ..., required_arg_N)
	# The presence of the required args will be checked when a signal
	# is fired.

	"cache-rollback": (),
	"start-tracking-changes": ("instance",),
	"stop-tracking-changes": ("instance",),
	"instance-deleted": ("inst_info",),
	"model-pre-init": ("instance", "kwargs"),
	"model-post-init": ("instance", "kwargs"),
	"model-pre-save": ("instance",),
	"model-post-save": ("instance", "created"),
	"model-pre-delete": ("instance",),
	"model-post-delete": ("instance", "deleted"),
	"model-pre-update": ("instance", "value", "fieldname"),
	"model-post-update": ("instance", "value", "fieldname"),
	
	# not implemented, because, what instance, should be cached, if there
	# is more than one with the same model type and primary key?
	"model-do-cache": ("instance",),
	
	"model-do-not-cache": ("instance",),
	"model-history-reset": ("instance",),
	"model-history-redo": ("instance",),
	"model-history-undo": ("instance",),
	"relation-pre-get": ("manager",),
	"relation-post-get": ("manager",),
	"relation-pre-set": ("manager", "values"),
	"relation-post-set": ("manager", "values"),
	"relation-pre-delete": ("manager",),
	"relation-post-delete": ("manager",),
	"relation-pre-add": ("manager", "values"),
	"relation-post-add": ("manager", "values"),
	"relation-pre-remove": ("manager", "values"),
	"relation-post-remove": ("manager", "values"),
}


registry = {}


def fire(signal, **kwargs):
	assert signal in registry, "Signal '%s' has not been registered." % signal

	# assert all required arguments have been given in ‘‘kwargs‘‘.
	for req_arg in SIGNALS[signal]:
		assert req_arg in kwargs, ("Required argument '%s' to signal '%s' "
									"has not been given.") %(req_arg, signal)

	cbname_from_signal = "_".join(signal.split("-"))

	for i, (wref, cb_name) in enumerate(registry[signal][:]):
		obj = wref()
		if obj is None:
			registry[signal].pop(i)
		else:
			cb_name = cb_name or cbname_from_signal
			cb = getattr(obj, cb_name, None)
			cb(**kwargs)


def register(signals, obj):
	for signal in signals:
		register_with_callback(signal, obj, None)


def register_with_callback(signal, obj, cb_name):
	"""
	Register ‘‘cb_name‘‘ to be called on ‘‘obj‘‘ when ‘‘signal‘‘ is fired.
	"""
	
	if object_is_registered_with_signal(obj, signal):
		raise Exception(
			"Object %s is already registered with signal '%s'." % (obj, signal)
		)
	registry.setdefault(signal, []).append((ref(obj), cb_name))


def deregister(signal, obj):
	for i, (wref, cb_name) in enumerate(registry[signal]):
		if wref() is obj:
			registry[signal].pop(i)
			break


def clean_up(signals=None):
	signals = signals or registry.keys()
	
	for signal in signals:
		for wref, cb_name in registry[signal][:]:
			obj = wref()
			if obj is None:
				registry[signal].remove((wref,cb_name))


def new_signal(signal):
	registry[signal] = []


def get_signals():
	return registry


def get_signals_for_object(obj):
	res = []
	for signal in registry:
		if object_is_registered_with_signal(signal):
			res.append(signal)
	return res


def object_is_registered_with_signal(obj, signal):
	if not signal in registry:
		return False
	return any(lambda wref, cb_name: wref() is obj, registry[signal])


def delete_signal(signal):
	del registry[signal]


# def setup_predefs():
	# for s in SIGNALS:
		# new_signal(s)
# setup_predefs()

