import pickle


class SafeCategoricalEncoder:
    def __init__(self):
        self.encoding_maps = {}
        self.fitted_columns = []
    
    def fit(self, df, categorical_cols, target):
        self.encoding_maps = {}
        self.fitted_columns = categorical_cols
        
        for col in categorical_cols:
            n_categories = df[col].nunique()
            
            if n_categories <= 5:
                # Ordered Label Encoding
                means = df.groupby(col)[target].mean().sort_values()
                self.encoding_maps[col] = {
                    'type': 'ordered_label',
                    'mapping': {cat: i for i, cat in enumerate(means.index)}
                }
            else:
                # Bayesian Target Encoding
                global_mean = df[target].mean()
                group_means = df.groupby(col)[target].mean()
                group_counts = df.groupby(col)[target].count()
                
                self.encoding_maps[col] = {
                    'type': 'bayesian',
                    'global_mean': global_mean,
                    'group_means': group_means.to_dict(),
                    'group_counts': group_counts.to_dict()
                }
        return self
    
    def transform(self, df):
        df_encoded = df.copy()
        
        for col, encoding_info in self.encoding_maps.items():
            if col in df.columns:
                if encoding_info['type'] == 'ordered_label':
                    df_encoded[col] = df[col].map(encoding_info['mapping'])
                else:
                    # Bayesian encoding
                    global_mean = encoding_info['global_mean']
                    group_means = encoding_info['group_means']
                    group_counts = encoding_info['group_counts']
                    
                    def encode_value(x):
                        if x in group_means:
                            count = group_counts.get(x, 0)
                            return (group_means[x] * count + global_mean * 50) / (count + 50)
                        return global_mean
                    
                    df_encoded[col] = df[col].apply(encode_value)
        
        return df_encoded
    
    def fit_transform(self, df, categorical_cols, target):
        return self.fit(df, categorical_cols, target).transform(df)
    
    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
    
    @classmethod
    def load(cls, path):
        with open(path, 'rb') as f:
            return pickle.load(f)
